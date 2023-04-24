"""Read content of a website and provide a short summary on one area of information"""
import io
from urllib.parse import urlparse

from ..utils import extract_content, parse_pdf, parse_html, summarize_text
from .command import BaseCommand


class ReaderCommand(BaseCommand,
    command='reader',
    description=f'Obtain info from a page based on URL or filename. Describe what to extract with the description field. If you need original text, explicitly say verbatim in the description; otherwise returns will be summarized. If one reading did not give you the desired content, try to change your instructions. Do not read a file if it only needs to be passed to a worker; pass the filename directly.',
    additional_context="""
reader example:
<user>: How do i configure a gagiji on tdotm?  Save it in `how_to.txt` for future reference
<assistant>: [
  {
    "command": "reader",
    "summary": "Extract how to configure a gagiji from tdotm manual",
    "content": [{
      "url": "tdotm_manual.pdf",
      "description": "Information about how to configure a gagiji",
      "save_as": "how_to.txt"
    }]
  }
]
"""
):
    summarization_model = 'gpt-3.5-turbo'
    summary_size = 600
    max_tokens = 2200

    def generate_prompt(self):
        if not isinstance(self.content, list):
            self.content = [self.content]
        success = 0
        output = []
        # Now go and summarize each page requested
        for entry in self.content:
            if isinstance(entry, str):
                url = entry
                description = self.summary
            elif isinstance(entry, dict):
                url = entry.get('url') or entry.get('filename')
                description = entry.get('description', 'key information')
            else:
                continue
            if not url:
                output.append('You must provide and url in the content of reader command')
                continue
            self.send_message(url=url, instruction=description)
            save_as = entry.get('save_as')
            content, content_type = extract_content(url)
            plain_types = ['text/plain', 'application/json', 'application/csv', 'text/markdown']
            if not content:
                text = ''
            elif content_type == 'application/pdf' or url.lower().endswith('.pdf'):
                text = parse_pdf(content)
            elif content_type in plain_types or url.lower().endswith('.txt'):
                text = content.decode()
            else:
                text = parse_html(content)
            if text:
                summary = summarize_text(
                    text,
                    description,
                    summary_size=self.summary_size,
                    model=self.summarization_model,
                    max_tokens=self.max_tokens,
                    callback=self.send_message
                )
                success += 1
            else:
                summary = "Unable to extract info. The page might be dynamic or restricted; try a different URL."
                self.send_message(info=f'Page {url} has no content')
            output.append(f'url: {url}\n Info: {summary}\n')
            if save_as:
                with open(save_as, 'w+') as f:
                    f.write(summary)
        if not output:
            output = ["You did not provide a valid `url` field in `context` for reader command. "]
        return '\n'.join(output)

