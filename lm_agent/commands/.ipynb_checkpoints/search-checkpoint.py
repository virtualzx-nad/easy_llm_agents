"""Search google for top results and links"""
import urllib.parse

import requests
from bs4 import BeautifulSoup

from .command import Command
from ..models import CompletionModel


class SearchCommand(
    Command,
    command='search',
    description='Search Goole to get top results and URLs to expand your knowledge. You must provide the exact search phrase and nothing else in `query` , and optionally tbs and tbm only when warranted. ',
    alias=['google'],
    example=[
        {'role': 'user', 'content': 'what happened in tech in the last hour?'},
        {'role': 'assistant', 'content': """[
  { 
    "notes": ["Always think and plan out actions when new information is received"],
    "command": "think",
    "summary": "Plan out how to fulfill user requests",
    "content": [
      "I do not have realtime information in the last hour so I will need to search to find them.",
      "Use `search` command to find websites with last hour's tech news",
      "Use `reader` command to read some of the relevant pages from the top search resuls",
      "Use `answer` command to report a list of tech news compiled from those pages"
    ]
  },
  { 
    "notes": [
      "Use `search` command to find",
      "`tech` is a good keyword for the search requirement.",
      "use `tbs` to specify the recency to ensure the results are from the last hour.",
      "use `tbm` to limit the search to news sites."
    ],
    "command": "search",
    "summary": "Find last hour's tech news",
    "content": {
      "query": "tech",
      "tbs": "qdr:h",
      "tbm": "nws"
    }
  }
]"""}],
):
    """Runs Google search and obtain the first page of the result and urls
    
    The AI sometimes provide multiple lines to intend to search multiple items at the same time.  We try and honor that
    """
    config = {'model': None}
    def generate_prompt(self):
        searches = self.content
        default_size = 3
        if not isinstance(searches, list):
            searches = [searches]
        keep = []
        if self.notes:
            self.send_message(summary=self.summary, notes=self.notes)
        for i, search in enumerate(searches):
            if isinstance(search, int):
                default_size = search
            elif isinstance(search, str):
                keep.append({'query': search })
            else:
                keep.append(search)
        results = []
        for search in keep:
            if search.get('query'):
                query = search['query']
            else:
                if self.summary:
                    query = self.infer_query(self.summary, self.notes)
                else:
                    continue
            tbs = search.get('tbs')
            tbm = search.get('tbm')
            size = search.get('size', default_size)
            self.send_message(query=query, size=size, tbs=tbs, tbm=tbm)
            results.extend(self.google_search(query, tbs=tbs, tbm=tbm, max_results=size))
        output = []
        titles = []
        for i, entry in enumerate(results):
            urls = ', '.join(entry['links'])
            output.append(f'{i+1}. {entry["title"]} [{urls}]\n{entry["content"]}')
            titles.append(entry['title'])
        result = '\n'.join(output) or 'No results. Try to divide complex searches into many incremental ones.'
        if output:
            result += '\n<< Please inspect each result and determine if you should read the page for more details.   Even if they do not give your the answer, they may help you refine your search.  If a search returns no relevant results, try break it into many simpler searches. >>'
        self.send_message(num_results=len(output), result_len=len(result), titles=titles)
        return '\n' + result

    def infer_query(self, summary, notes):
        """If the command didn't include a query then we have to rebuild the content from notes"""
        notes_str = ''
        if isinstance(notes, str):
            notes_str = notes
        else:
            for item in notes:
                notes_str += f'  - {item}\n'
        instruction = f"""Please determine the Google search keywords for a specific goal
Example output for “Find a camera between 10 to 20 dollars or a twitter post about a good camera”:

(camera $10…$20) OR (good camera @twitter)

End of example.
Now please determine the search query for "{summary}"

Here are some of my notes on my thinking:
{notes_str}

Please return ONE query string."""
        model = CompletionModel.get(self.config.get('model') or self.config['default_model'])
        return model.get_completion(instruction, text_only=True)

    @staticmethod
    def google_search(query, max_results=10, url="https://www.google.com/search?q={query}", tbs=None, tbm=None):
        """A quick an simple scraper to get the top results from a search result page"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        escaped_query = urllib.parse.quote(query)
        if tbs:
            escaped_query += f'&tbs={tbs}'
        if tbm:
            escaped_query += f'&tbm:{tbm}'
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
