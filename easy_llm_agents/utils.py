"""Utility functions"""
import io
import re
import os
import sys
import ast
import json
import math
import mimetypes

import requests
import tiktoken
from bs4 import BeautifulSoup


from .clients import get_completion


class ChangeDir:
    """A context manager for changing the current directory while also preserving the current path in search path
    Note this was written by GPT and looks legit in a glance.  Check more carefully when time permits.
    """
    def __init__(self, path):
        self.path = path
        self.current_dir = os.getcwd()
        self.current_dir_in_sys_path = self.current_dir in sys.path
    
    def __enter__(self):
        os.chdir(self.path)
        if not self.current_dir_in_sys_path:
            sys.path.append(self.current_dir)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.current_dir)
        if not self.current_dir_in_sys_path:
            sys.path.remove(self.current_dir)


_encodings = {}

def token_count(text, model='gpt-3.5-turbo'):
    """Compute how many tokens a piece of text would take"""
    if model not in _encodings:
        _encodings[model] = tiktoken.encoding_for_model(model)
    encoding = _encodings[model]
    return len(encoding.encode(text))


def extract_content(url):
    """Extract contents from an url, returning raw bytes
    """
    if url.startswith('file://') or ':' not in url:
        content_type, content_encoding = mimetypes.guess_type(url)
        if url.startswith('file:///'):
            path = url[len('file:///'):]
        elif url.startswith('file://'):
            path = url[len('file://'):]
        else:
            path = url
        with open(path, 'rb') as f:
            return f.read(), content_type
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
    except:
        return '', 'unknown'
    if response.status_code >= 200 and response.status_code < 300:
        content_type = response.headers.get('content-type')
        return response.content, content_type
    return '', 'unknown'


def parse_html(content):
    """Parse and HTML page preserving new lines and hyperlinks"""
    # Use BeautifulSoup to parse the webpage content
    soup = BeautifulSoup(content, "html.parser")
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


def parse_pdf(content):
    """Extract text from a pdf in url"""
    try:
        import PyPDF2
    except ImportError:
        return

    pdf_file = io.BytesIO(content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ''
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


class SkipMissingDict(dict):
    # This method is called when a key is not found in the dictionary
    def __missing__(self, key):
        # Return the key surrounded by curly braces to keep it unchanged
        return '{' + key + '}'


def summarize_text(text, description="", summary_size=600, model='gpt-3.5-turbo', max_tokens=2200, callback=None):
    lines = text.split('\n')
    included = []
    lines.append('')
    current_summary = ''
    base_text = (
        f"Extract from text below based on this instruction `{description}`. "
        f"Keep your response within {summary_size} tokens.  Return verbatim text or sentence if the instruction asks for a specific section or if the content is source code.  Keep all formatting and indentation in code blocks.  \n"
        "Text:\n```" + current_summary + '\n'
            )
    start = 0
    total_tokens = token_count(base_text, model)

    toks = [token_count(line, model) for line in lines]
    if callback:
        callback(lines=len(lines)-1, tokens=sum(toks), n=int(math.ceil(sum(toks)/(max_tokens-total_tokens))))
    for i, (line, tokens) in enumerate(zip(lines, toks)):
        line = line.strip() + '\n'
        if total_tokens + tokens <= max_tokens and i < len(lines) - 1:
            if line:
                included.append(line)
                total_tokens += tokens
        else:
            summary_text = base_text +  ''.join(included) + "```"
            # callback(estimated_tokens=total_tokens, actual_tokens=token_count(summary_text))
            current_summary = get_completion(summary_text, model=model, max_tokens=int(summary_size*2), text_only=True)
            current_summary = current_summary.strip('```')
            base_text = (
                f"Extract from text below based on this instruction `{description}`. "
                f"Keep your response within {summary_size} tokens.  If the instruction asks for a specific section, return it verbatim. Keep source code unchanged and verbatim.  Keep all formatting and indentation in code blocks.  \n"
                "Text:\n```" + current_summary + '\n'
            )
            included = [line]
            start = i
            total_tokens = tokens + token_count(base_text, model)
    return current_summary


def get_relevant_files(files, purpose, instruction, context):
    """Given a dictionary of files identify which ones are relevant for a specific purpose"""
    if not files:
        return []
    file_desc = '\n'.join(f'  - {name}: {desc}' for name, desc in files.items())
    prompt =f"""You are a helpful assistant that will identify relevant file needed for task: {purpose}.
To do this, you will be given a list of existing files and their description, a set of instructions on how this new file will be created, and some context information.
You will identify, given the context information, which file within the list of provided files contain relevant information in order for the user to follow the instruction and finish the task.

files:
{file_desc}

context: {context}

instructions: ```{instruction}```

Please return the list in a Python list with the elements being the filenames. Return the list and nothing else. If there is no relevant file, return an empty list.  Avoid any descriptions or explanantions. 

and example return: ["file1", "file2"]

"""
    response = get_completion(prompt, model='gpt-3.5-turbo', max_tokens=500, temperature=0.2, text_only=True)
    # print('RESPONSE: ', response)
    try:
        result = ast.literal_eval(response)
    except Exception:
        try:
            result = json.loads(response)
        except Exception as e:
            print('Exception occured when trying to determine relevant files: ', e)
            result = []
    return [name for name in result if name in files]
