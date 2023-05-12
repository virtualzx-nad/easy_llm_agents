"""Search google for top results and links"""
import urllib.parse

import requests
from bs4 import BeautifulSoup

from .command import Command
from ..models import CompletionModel
from ..utils import google_search

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
    config = {'model': None, 'default_size': 3}
    def generate_prompt(self):
        searches = self.content
        default_size = self.config.get('default_size', 3)
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
            results.extend(google_search(query, tbs=tbs, tbm=tbm, max_results=size))
        output = []
        titles = []
        for i, entry in enumerate(results):
            urls = ', '.join(entry.get('links', []))
            output.append(f'{i+1}. {entry["title"]} [{urls}]\n{entry["content"]}')
            titles.append(entry['title'])
        result = '\n'.join(output) or 'No results. << Try to divide complex searches into many incremental ones. >>'
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
