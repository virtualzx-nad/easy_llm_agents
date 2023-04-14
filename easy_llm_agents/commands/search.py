"""Search google for top results and links"""
import urllib.parse

import requests
from bs4 import BeautifulSoup

from .command import BaseCommand


class SearchCommand(BaseCommand, command='search', description='Search Goole to get top results and URLs. Try your best to construct the most effective query based on your knowledge and choose a sensible result count limit.'):
    """Runs Google search and obtain the first page of the result and urls
    
    The AI sometimes provide multiple lines to intend to search multiple items at the same time.  We try and honor that
    """
    def generate_prompt(self):
        searches = self.content

        if not isinstance(searches, list):
            searches = [searches]
        for i, search in enumerate(searches):
            if isinstance(search, str):
                searches[i] = {'query': search }
        results = []
        for search in searches:
            if not search.get('query'):
                continue
            self.send_message(info=f'Googling {search["query"]}')
            results.extend(self.google_search(search['query'], max_results=search.get('size', 3)))
        output = []
        for entry in results:
            urls = ', '.join(entry['links'])
            output.append(f'{entry["title"]} [{urls}]\n{entry["content"]}\n')
        return '\n'.join(output) or 'No results. Try to divide complex searches into many incremental ones.'

    @staticmethod
    def google_search(query, max_results=10, url="https://www.google.com/search?q={query}"):
        """A quick an simple scraper to get the top results from a search result page"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        escaped_query = urllib.parse.quote(query)
        res = requests.get(url.format(query=escaped_query), headers=headers)

        soup = BeautifulSoup(res.text, 'html.parser')
        search_results = []
        n_result = 0
        # for erach search result, extract title, links and text summary.  Try to make sure it works for tables
        for result in soup.find_all('div', {'class': 'MjjYud'}):
            title = result.find('h3')
            if title:
                entry = {'title': title.text}
                a_blocks = result.find_all('a', href=True)
                entry['links'] = list(set(link['href'] for link in a_blocks if link['href'].startswith('http')))
                lines = []
                for content in result.find_all('div', {'class': 'Z26q7c UK95Uc'}):
                    for tr in content.find_all('tr'):
                        tr.insert_after('\n')
                    lines.append(' '.join(content.strings))
                entry['content'] = '\n'.join(lines)
                search_results.append(entry)
                n_result += 1
                if n_result == max_results:
                    break
        return search_results
