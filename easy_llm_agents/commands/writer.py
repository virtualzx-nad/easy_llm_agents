"""A writer that writes an entire file for you"""
import re

import tiktoken           # openai tokenizer.  for counting tokens

from .command import BaseCommand
from ..clients import get_completion



def get_tail(text):
    # Split the text into sentences using regex
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    # Get the last two sentences
    last_three = sentences[-3:]
    # Join the sentences and return the result
    return " ".join(last_three)


class WriterCommand(
    BaseCommand,
    command='writer',
    description='Ask a writer to write a file for you, either code or text. You can write any non-binary files, for example a user manual, a book, an email, a README.md file, a javascript or Python source file, etc. Please provide sufficient context so that the writer can properly write the file correctly. Must provide these fields in context: `filename` name of the file to write including suffix which determines the file format; `instruction` string describing precisely what to write in the file; `context` string to provide detailed context for the writer to correctly write the file; `context_file` list all files that contain relevant context.',
    additional_context="""
writer example:
<user>: Create `yadaa_api.js` that enables Yadaa endpoint.  Specs in `technical_design.txt` 
<assistant>: [
  {
    "command": "writer",
    "summary": "Write source code to enable Yadaa endpoint",
    "content": {
      "filename": "route.js",
      "instruction": "Write source code file that enables Yadaa endpoint",
      "context": "Technical specifications can be found in `technical_design.txt`",
      "context_file": ["technical_design.txt"]
    }
  }
]
"""
):
    def generate_prompt(self):
        if not isinstance(self.content, list):
            content = [self.content]
        else:
            content = self.content
        missing = False
        output = []
        encoding = tiktoken.encoding_for_model('gpt-4')
        summarization_encoding = tiktoken.encoding_for_model('gpt-3.5-turbo')
        
        tasks = []

        for entry in content:
            if 'filename' not in entry or 'instruction' not in entry:
                missing = True
                continue
            filename = entry['filename']
            instruction = entry['instruction']
            context = entry.get('context', '')
            context_file = entry.get('context_file')
            if context_file:
                if isinstance(context_file, str):
                    context_file = [context_file]
                for context_fname in context_file:
                    try:
                        with open(context_fname) as f:
                            context += f'\nContent of {context_fname}:\n' + f.read() + '\n'
                    except Exception as e:
                        output.append(f"Context file {context_fname} cannot be loaded")
            if isinstance(filename, list):
                for fname in filename:
                    tasks.append([fname, instruction, context])
            else:
                tasks.append([filename, instruction, context])
            
        for filename, instruction, context in tasks:
            self.send_message(filename=filename, instruction=instruction, context=context[:100])
            current_summary = ''
            tail = ''
            context_prompt = f"You will be given an instruction and to create file `{filename}`."
            context_prompt += 'Please ensure the format and the content match the suffix of the file'
            if context:
                context_prompt = "Here are some context that will help you write it: \n" + context
            context_tokens = len(encoding.encode(context_prompt)) + 1
            with open(filename, 'w') as f:
                pass
            while True:
                prompt = instruction
                if current_summary:
                    prompt += '\nHere is a summary of the portion of the file you have already written:' + current_summary
                prompt_tokens = len(encoding.encode(prompt))
                tail_tokens = len(encoding.encode(tail))
                top_choice = get_completion(
                    [{'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': tail}],
                    model='gpt-4',
                    system_prompt=context_prompt,
                    temperature=0.7,
                    max_tokens=8000 - context_tokens - prompt_tokens - tail_tokens,
                    text_only=False,
                )['choices'][0]
                text = top_choice['message']['content']
                with open('writer.log', 'a+') as wl:
                    wl.write(f'FILENAME:{filename}\n')
                    wl.write(f'PROMPT:{prompt}\n')
                    wl.write(f'CONTEXT:{context_prompt}\n')
                    wl.write(f'COMPLETION:{text}\n')
                with open(filename, 'a') as f:
                    f.write(text)
                if top_choice['finish_reason'] != 'length':
                    break
                tail = get_tail(text)
                summary_prompt = (
                    'Please summarize the following unfinished text with sufficient details so that '
                    'a different person can use it to finish the text. text: ' + current_summary + '\n' + text
                )
                current_summary = get_complextion(
                    summary_prompt,
                    model='gpt-3.5-turbo',
                    temperature=0.2,
                    max_tokens=4000-len(summarization_encoding.encode(summary_prompt)),
                    text_only=True,
                )
            output.append(f'File {filename} was written')
        if missing:
            output.append('filename and instructions must be provided in command content.')
        return '\n'.join(output)
