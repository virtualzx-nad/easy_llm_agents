"""Read content of a website and provide a short summary on one area of information"""
import re
import math
from urllib.parse import urlparse

import tiktoken           # openai tokenizer.  for counting tokens
import requests
from bs4 import BeautifulSoup

from ..clients import get_completion
from .command import BaseCommand

# # enable google doc and drive if in cl infra
# try:
#     from clpy.core.google.docs import get_doc_contents, contents_to_plain_text
#     from clpy.core.google.drive import get_file_contents
#     cl_env = True
# except:
#     cl_env = False

class ReadPageCommand(BaseCommand,
    command='READ_PAGE',
    description=f'Obtain info from a web page.  Describe infomation needed in the line following the URL.' 
):
    summarization_model = 'gpt-3.5-turbo'
    summary_size = 200
    max_tokens = 2000

    def generate_prompt(self):
        lines = self.content.split('\n')
        url_dict = {}
        current_url = None
        current_description = ''
        for line in lines:
            # clean up the line
            line = line.strip()
            if not line:
                continue
            if line.startswith('URL:') and line[4:].strip().startswith('http'):
                line = line[4:].strip()
            if line.startswith('http'):
                if current_url:
                    url_dict[current_url] = current_description.strip()
                # If the line is a URL, set it as the current URL and initialize its description
                current_url = line
                current_description = ''
            else:
                current_description += line + '\n'
        if current_url:
            url_dict[current_url] = current_description.strip()
        if not url_dict:
            return """Please include a valid URL with the following syntax:
!READ_PAGE Reason for reading the page
https://website.to.visit/some-page
Optional instructions on what information to retrieve from page
"""
        success = 0
        output = ''
        # Now go and summarize each page requested
        for url, description in url_dict.items():
            self.send_message(info=f'Extract and summarize {url} with instruction `{description}`')
            if len(url_dict) > 1:
                output += 'Page ' + url + ':'
            text = self.extract_page(url)
            if text:
                summary = self.summarize_text(text, description)
                output += summary + '\n'
                success += 1
            else:
                output += "Unable to extract. The page might be dynamic or restricted; try a different URL.\n\n"
                self.send_message(info=f'Page {url} has no content')
        if not success:
            output += 'Please try different URLs or a different command.'
        return output.strip() or 'Did not find any content. Try a different page'

    @staticmethod
    def extract_page(url):
        """Extract content of a page from its URL, preserving new lines and hyperlinks"""
        # if url.startswith('https://docs.google.com/'):
        #     doc_id = url.split("/")[5]
        #     contents = get_doc_contents(doc_id)
        #     return contents_to_plain_text(contents)
        # if url.startswith('https://drive.google.com/'):
        #     file_id = url.split("/")[5]
        #     contents = get_file_contents(file_id, return_text=True)
        #     return contents
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
        }
        try:
            response = requests.get(url, headers=headers)
        except:
            return
        if response.status_code >= 200 and response.status_code < 300:
            # Use BeautifulSoup to parse the webpage content
            soup = BeautifulSoup(response.text, "html.parser")
            if soup:
                # Extract all the text and links from the HTML content
                for link in soup.find_all('a'): # move links from a elements to text
                    if 'href' in link:
                        link.insert_after(' (' + link['href'] + ')')
                for tag in soup.find_all(['p', 'br']):  # render line breaks
                    tag.insert_after('\n')
                text = soup.get_text('\n')
                text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)   # consolidate new lines
                return text

    def summarize_text(self, text, description=""):
        encoding = tiktoken.encoding_for_model(self.summarization_model)
        lines = text.split('\n')
        total_tokens = 0
        included = []
        lines.append('')
        current_summary = ''
        start = 0
        toks = [len(encoding.encode(line)) for line in lines]
        self.send_message(info=f'Total lines: {len(lines)-1}. Tokens: {sum(toks)}. Summarizations~ {int(math.ceil(sum(toks)/2000))}')
        for i, (line, tokens) in enumerate(zip(lines, toks)):
            line = line.strip()
            if not line:
                continue
            if total_tokens + tokens <= self.max_tokens and i < len(lines) - 1:
                included.append(line)
                total_tokens += tokens
            else:
                if description:
                    summary_text = (
                        "Please extract information that fits this description or instruction from the text below."
                        f"Keep your response within {self.summary_size} tokens. Make sure to keep any names, key figures, important details, requirements, responsibilities, asks or preferences.  Keep links to important items in the result.\n"
                        f"Description:\n`{description}`\n"
                        "Text:\n```" + current_summary + '\n' +  '\n'.join(included) + "```"
                    )
                else:
                    summary_text = (
                        f"Please extract key information and summarization from the following website in about {self.summary_size} tokens. "
                        "make sure to keep any names, key figures, important details, requirements, responsibilities, asks or preferences.\n"
                        "Keep links to important items in the result.\n"
                        "Text:\n```" + current_summary + '\n' +  '\n'.join(included) + "```"
                    )
                self.send_message(info=f'Performing summarization for line #{start+1} to {i} with approx {int(total_tokens)} tokens in text')
                current_summary = get_completion(summary_text, model=self.summarization_model, max_tokens=int(self.summary_size*3), text_only=True)
                current_summary = current_summary.strip('```')
                included = [line]
                start = i
                total_tokens = tokens
        return current_summary
