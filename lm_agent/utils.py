"""Utility functions"""
import io
import re
import os
import sys
import ast
import json
import math
import urllib
import mimetypes

import requests
from bs4 import BeautifulSoup

from .models import CompletionModel

class ChangeDir:
    """A context manager for changing the current directory while also preserving the current path in search path
    Note this was written by GPT and looks legit in a glance.  Check more carefully when time permits.
    """
    def __init__(self, path):
        self.path = path
        self.current_dir = os.getcwd()
        self.current_dir_in_sys_path = self.current_dir in sys.path
    
    def __enter__(self):
        if not self.path:
            return
        os.chdir(self.path)
        if not self.current_dir_in_sys_path:
            sys.path.append(self.current_dir)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.path:
            return
        os.chdir(self.current_dir)
        if not self.current_dir_in_sys_path:
            sys.path.remove(self.current_dir)



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


def summarize_text(text, description="", summary_size=600, model='gpt-3.5-turbo', callback=None):
    if isinstance(model, str):
        model = CompletionModel.get(model)
    max_tokens = model.max_tokens
    lines = text.split('\n')
    included = []
    lines.append('')
    current_summary = ''
    base_text = (
        f"Extract from text below based on this instruction `{description}`. "
        f"Keep your response within {summary_size} tokens and do not repeat information.  Keep names, URLs and figures if possible when relevant.  Return verbatim text or sentence if the instruction asks for a specific section.  Any relevant source code should be returned verbatim, with all formatting and indentation kept unchanged.  Do not give any additional explanation unless explicitly asked. For example: `Extract the keyword`; valid resposne `KATZ`; invalid response `The keyword is KATZ`.  \n"
        "Text:\n```" + current_summary + '\n'
            )
    start = 0
    total_tokens = model.token_count(base_text) + 2 * summary_size

    toks = [model.token_count(line) + 8 for line in lines]
    if callback:
        callback(lines=len(lines)-1, tokens=sum(toks), n=int(math.ceil(sum(toks)/(max_tokens-total_tokens-8))))
    for i, (line, tokens) in enumerate(zip(lines, toks)):
        line = line.rstrip() + '\n'
        if total_tokens + tokens <= max_tokens and i < len(lines) - 1:
            if line:
                included.append(line)
                total_tokens += tokens
        else:
            summary_text = base_text +  ''.join(included) + "```"
            # callback(estimated_tokens=total_tokens, actual_tokens=token_count(summary_text))
            current_summary = model.get_completion(summary_text, max_tokens=summary_size*2, text_only=True)
            current_summary = current_summary.strip('```')
            base_text = (
                f"Extract information from text below based on this instruction `{description}`. "
                f"If the instruction asks for a specific section, return it verbatim. Keep source code unchanged and verbatim.  Keep all formatting and indentation in code blocks.  Return the results in plain text and do not return anything else\n"
                "Text:\n```" + current_summary + '\n'
            )
            included = [line]
            start = i
            total_tokens = tokens + model.token_count(base_text)
    return current_summary


def get_relevant_files(files, purpose, instruction, context, model='gpt-3.5-turbo'):
    """Given a dictionary of files identify which ones are relevant for a specific purpose"""
    if not isinstance(model, CompletionModel):
        model = CompletionModel.get(model)
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
    response = model.get_completion(prompt, max_tokens=500, temperature=0.2, text_only=True)
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


def find_all_dicts(content):
    """Find all valid Python dictionaries in a text string; there might be many of them
    """
    # print(f'Looking for all dicts in ```{content}```')
    results = []
    first, content = find_next_dict(content)
    while first is not None:
        if first:
            results.append(first)
        first, content = find_next_dict(content)
    print(f'found {len(results)} dicts')
    return results


def find_next_dict(content):
    """In a text string 
    Start with the first open curly `{` and see if there is a close somewhere that would 
    enclose a Python dict.  
    """
    start = content.find('{')
    content = content[start:]
    if start < 0:
        return None, ''
    end = content.find('}') + 1
    while end > 0:
        trial = content[:end]
        result = parse_python(trial)
        if result is not None:
            return result, content[end:]
        end = content.find('}', end) + 1
    next_start = content.find('{', 1)
    if next_start > 0:
        return find_next_dict(content[next_start:])
    return None, ''


def parse_python(content):
    """Try and parse a string into python object"""
    try:
        result = ast.literal_eval(content)
        return result
    except Exception as e:
        pass
    try:
        result = json.loads(content)
        return result
    except Exception as e:
        pass


def google_search(query, max_results=10, url="https://www.google.com/search?q={query}", tbs=None, tbm=None):
    """A quick an simple scraper to get the top results from a search result page"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    escaped_query = urllib.parse.quote(query)
    if tbs:
        escaped_query += f'&tbs={tbs}'
    if tbm:
        escaped_query += f'&tbm={tbm}'
    res = requests.get(url.format(query=escaped_query), headers=headers)

    soup = BeautifulSoup(res.text, 'html.parser')
    search_results = []
    n_result = 0
    # for erach search result, extract title, links and text summary.  Try to make sure it works for tables
    if tbm == 'nws':
        for result in soup.find_all('div', {'class': 'SoaBEf'}):
            freshness = result.find('div', {'style': 'bottom:0px'})
            title = result.find('div', {'role': 'heading'})
            a_blocks = result.find_all('a', href=True)
            entry = {
                'title': f'{title.text} ({freshness.text})',
                'links': list(set(link['href'] for link in a_blocks if link['href'].startswith('http')))
            }
            lines = []
            for content in result.find_all('div', {'class': 'GI74Re nDgy9d'}):
                for tr in content.find_all('tr'):
                    tr.insert_after('\n')
                lines.append(' '.join(content.strings))
            entry['content'] = '\n'.join(lines)
            search_results.append(entry)
            n_result += 1
            if n_result == max_results:
                break
    else:
        info = soup.find('div', {'class': 'yxjZuf'})
        if info:
            entry = {'title': 'General information', 'links': []}
            lines = []
            for content in info.find_all('span'):
                if content.parent.name == 'span':
                    continue
                line = ' '.join(content.strings)
                cc = content.get('class', '')
                if isinstance(cc, list):
                    cc = ''.join(cc)
                if cc == 'Y2Bcn':
                    continue
                if cc != 'w8qArf':
                    line += '\n'
                if line.strip():
                    lines.append(line)
            entry['content'] = ''.join(lines)
            search_results.append(entry)
        # search_results.append()
        for result in soup.find_all('div', {'class': 'MjjYud'}):
            title_block = result.find('div', {'class': 'yuRUbf'})
            title = result.find('h3')
            if title:
                entry = {'title': title.text}
                lines = []
                if title_block:
                    a_blocks = title_block.find_all('a', href=True)
                    entry['links'] = list(set(link['href'] for link in a_blocks if link['href'].startswith('http')))
                    for content in result.find_all('div', {'class': lambda value: value and value.startswith("Z26q7c UK95Uc")}):
                        if content.find('h3'):
                            continue
                        for tr in content.find_all('tr'):
                            tr.insert_after('\n')
                        lines.append(' '.join(content.strings))
                    info_block = result.find('div', {'class': 'V3FYCf'}) or []
                    for item in info_block:
                        ic = item.get('class', '')
                        if ic == 'g' or isinstance(ic, list) and 'g' in ic:
                            continue
                        lines.append(' '.join(item.strings))
                    entry['content'] = '\n'.join(lines)
                else:
                    entry['content'] = ''
                search_results.append(entry)
                n_result += 1
                if n_result == max_results:
                    break
    return search_results

