"""Read content of a website and provide a short summary on one area of information"""
import io
import re
from urllib.parse import urlparse

from ..utils import extract_content, parse_pdf, parse_html, summarize_text
from .command import Command


class ReaderCommand(Command,
    command='reader',
    alias=['read', 'summarize'],
    description=f'Obtain info from a page based on URL or filename. Put the full url in `url` field, which usually you would obtain from previous commands or search. Describe what information to extract with the `extract` field succinctly. If you need original text, explicitly say verbatim; otherwise returns will be summarized. Do not read a file if it only needs to be passed to a worker; pass the filename directly.',
    example=[
        {'role': 'user', 'content': 'How do i configure a gagiji on tdotm?  Save it in `how_to.txt` for future reference'},
        {'role': 'assistant', 'content': """[
  {
    "notes": [],
    "command": "think",
    "summary": "Plan out steps",
    "content": [
      "I need to perform search",
      "Use `search` to find info about 'configure gagiji on tdotm'",
      "Use `reader` to find clear instructions on how to configure gagiji on tdotm and save results to `how_to.txt`",
      "Use `answer` to respond to the user."
    ]
  },
  {
    "notes": ["find info about 'configure gagiji on tdotm'"],
    "command": "search",
    "summary": "Find information about how to configure gagiji on tdotm",
    "content": {"query": "configure gagiji on tdotm"}
  }
]"""},
        {'role': 'system', 'content': """`search` returns: TDOTM Rated the best tool for configuring gagiji [https://www.oox.cd/news/tdotm-rated-best-gagiji-2021]

tdotm Manual [https://tdotm.io/en/manual/tdotm_manual.pdf]
21 hours ago  —  Chapter 3   Configuring gagiji. First turn on your computer...

Please inspect each search result to determine if they are relevant.
"""},
        {'role': 'assistant', 'content': """{
  "notes": [
      "Found tdotm manual with information about how to configure gagiji.",
      "Use `reader` to learn how to configure gagiji on tdotm and save results to `how_to.txt`"
  ],
  "command": "reader",
  "summary": "Learn how to configure a gagiji from tdotm manual",
  "content": [{
    "url": "https://tdotm.io/en/manual/tdotm_manual.pdf",
    "extract": "configure a gagiji",
    "save_as": "how_to.txt"
  }]
}"""},
        {'role': 'system', 'content': "`reader` returns: To configure gagiji, first turn on your computer, then open tdotm menu, then choose gagiji from the menu and put in your address.  Result saved to `how_to.txt`"},
        {'role': 'assistant', 'content': """{
  "notes": [
      "Information about configuring gagiji extracted and saved to `how_to.txt`",
      "Use the `answer` command to report finding to the user."
  ],
  "command": "answer",
  "summary": "Report successful execution of instructions and provide information",
  "content": "To configure gagiji, first turn on your computer, then open tdotm menu, then choose gagiji from the menu and put in your address.  Result saved to `how_to.txt`"
}"""},
],
):
    config = {
        'summarization_model': 'gpt-3.5-turbo',
        'summary_size': 600,
    }

    def generate_prompt(self):
        if not isinstance(self.content, list):
            self.content = [self.content]
        success = 0
        output = []
        # Now go and summarize each page requested
        for entry in self.content:
            if isinstance(entry, str):
                enclosed = re.findall(r"\[(https?://[^\s]+)\]", entry)
                if enclosed:
                    url = list(enclosed)
                else:
                    url = entry
                extract = self.summary
            elif isinstance(entry, dict):
                url = entry.get('url') or entry.get('filename')
                extract = entry.get('extract', 'key information')
            else:
                continue
            if not url:
                output.append('You must provide and url in the content of reader command')
                continue
            self.send_message(url=url, instruction=extract)
            if isinstance(entry, dict):
                save_as = entry.get('save_as')
            else:
                save_as = None
            if not isinstance(url, list):
                url = [url]
            for item in url:
                content, content_type = extract_content(item)
                plain_types = ['text/plain', 'application/json', 'application/csv', 'text/markdown']
                if not content:
                    text = ''
                elif content_type == 'application/pdf' or item.lower().endswith('.pdf'):
                    text = parse_pdf(content)
                elif content_type in plain_types or item.lower().endswith('.txt'):
                    text = content.decode()
                else:
                    text = parse_html(content)
                if text:
                    summary = summarize_text(
                        text,
                        extract,
                        summary_size=self.config.get('summary_size', 600),
                        model=self.config.get('summarization_model', 'gpt-3.5-turbo'),
                        callback=self.send_message
                    )
                    success += 1
                else:
                    summary = "Unable to extract info. The page might be dynamic or restricted; try a different URL."
                    self.send_message(info=f'Page {item} has no content')
                output.append(f'item: {item}\n Info: {summary}\n')
            if save_as:
                with open(save_as, 'w+') as f:
                    f.write(summary)
        if not output:
            output = ["You did not provide a valid `url` field in `context` for reader command. "]
        return '\n'.join(output)

