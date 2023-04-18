"""Read content of a website and provide a short summary on one area of information"""
import io
import math
from urllib.parse import urlparse

from ..clients import get_completion
from ..utils import extract_content, parse_pdf, parse_html, token_count
from .command import BaseCommand


class ReaderCommand(BaseCommand,
    command='reader',
    description=f'Obtain info from a page based on URL or filename. Describe what to extract with the description field. If you need original text, explicitly say verbatim in the description; otherwise returns will be summarized. If one reading did not give you the desired content, try to change your instructions. Do not read a file if it only needs to be passed to a worker; pass the filename directly.',
    additional_context="""
reader example:
<user>: How do i configure a gagiji on tdotm?
<assistant>: [
  {
    "command": "reader",
    "summary": "Extract how to configure a gagiji from tdotm manual",
    "content": [{
      "url": "tdotm_manual.pdf",
      "description": "Information about how to configure a gagiji"
    }]
  }
]
"""
):
    summarization_model = 'gpt-3.5-turbo'
    summary_size = 600
    max_tokens = 2300

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
            self.send_message(info=f'Extract and summarize {url} with instruction `{description}`')
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
                summary = self.summarize_text(text, description)
                success += 1
            else:
                summary = "Unable to extract info. The page might be dynamic or restricted; try a different URL."
                self.send_message(info=f'Page {url} has no content')
            output.append(f'url: {url}\n Info: {summary}\n')
        if not output:
            output = ["You did not provide a valid `url` field in `context` for reader command. "]
        return '\n'.join(output)


    def summarize_text(self, text, description=""):
        lines = text.split('\n')
        included = []
        lines.append('')
        current_summary = ''
        base_text = (
            f"Extract from text below based on this instruction `{description}`. "
            f"Keep your response within {self.summary_size} tokens.  Return verbatim text or sentence if the instruction asks for a specific section or if the content is source code.  Keep all formatting and indentation in code blocks.  \n"
            "Text:\n```" + current_summary + '\n'
                )
        start = 0
        total_tokens = token_count(base_text, self.summarization_model)

        toks = [token_count(line, self.summarization_model) for line in lines]
        self.send_message(info=f'Total lines: {len(lines)-1}. Tokens: {sum(toks)}. Summarizations~ {int(math.ceil(sum(toks)/(self.max_tokens-total_tokens)))}')
        for i, (line, tokens) in enumerate(zip(lines, toks)):
            line = line.strip()
            if total_tokens + tokens <= self.max_tokens and i < len(lines) - 1:
                if line:
                    included.append(line)
                    total_tokens += tokens
            else:
                summary_text = base_text +  '\n'.join(included) + "```"
                # self.send_message(info=f'Performing summarization for line #{start+1} to {i} with approx {int(total_tokens)} tokens in text')
                current_summary = get_completion(summary_text, model=self.summarization_model, max_tokens=int(self.summary_size*2), text_only=True)
                current_summary = current_summary.strip('```')
                base_text = (
                    f"Extract from text below based on this instruction `{description}`. "
                    f"Keep your response within {self.summary_size} tokens.  Return verbatim text or sentence if the instruction asks for a specific section or if the content is source code.  Keep all formatting and indentation in code blocks.  \n"
                    "Text:\n```" + current_summary + '\n'
                )
                included = [line]
                start = i
                total_tokens = tokens + token_count(base_text, self.summarization_model)
        return current_summary
