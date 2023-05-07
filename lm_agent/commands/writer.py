"""A writer that writes an entire file for you"""
import re
import os

from .command import Command
from ..utils import summarize_text, get_relevant_files
from ..models import CompletionModel


def get_tail(text):
    # Split the text into sentences using regex
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    # Get the last two sentences
    last_three = sentences[-3:]
    # Join the sentences and return the result
    return " ".join(last_three)


class WriterCommand(
    Command,
    command='writer',
    description='Ask a writer to write a file for you, either code or text. You can write any non-binary files, for example a user manual, a book, an email, a README.md file, a javascript or Python source file, etc. Please provide sufficient context so that the writer can properly write the file correctly. Must provide these fields in context: `filename` name of the file to write including suffix which determines the file format; `instruction` string describing precisely what to write in the file; `context` string to provide detailed context for the writer to correctly write the file; `context_file` list all files that contain relevant context. Always try to write one file at a time to provide more precise instructions and context.',
    example=[
        {'role': 'system', 'content': "Technical specs are stored in `technical_design.txt`. Async is required."},
        {'role': 'user', 'content': "Create `yadaa_api.js` that enables Yadaa endpoint."},
        {'role': 'assistant', 'content': """[
  {
    "command": "think",
    "summary": "Analyze user instruction",
    "content": ["Use javascript to implement an endpoint, following technical specifications and with asynchronous programming."]
  },
  {
    "command": "writer",
    "summary": "Write source code to enable Yadaa endpoint",
    "content": {
      "filename": "route.js",
      "instruction": "Write source code file that enables Yadaa endpoint and use async",
      "context": "Technical specifications can be found in `technical_design.txt`",
      "context_file": ["technical_design.txt"]
    }
  }
]"""}],
):
    config = {
        'model': None,
        'summarization_model': 'gpt-3.5-turbo',
        'temperature': 0.7,
    }
    def generate_prompt(self):
        if not isinstance(self.content, list):
            content = [self.content]
        else:
            content = self.content
        
        self.model = CompletionModel.get(self.config.get('model') or self.config['default_model'])

        sum_model_name = self.config.get('summarization_model', 'gpt-3.5-turbo')
        if isinstance(sum_model_name, CompletionModel):
            self.summarization_model = sum_model_name
        else:
            self.summarization_model = CompletionModel.get(sum_model_name)

        missing = False
        output = []
        
        tasks = []

        for entry in content:
            if 'filename' not in entry or 'instruction' not in entry:
                missing = True
                continue
            filename = entry['filename']
            instruction = entry['instruction']
            context = entry.get('context', '')
            context_file = entry.get('context_file', [])
            if context_file:
                if isinstance(context_file, str):
                    context_file = [context_file]
            else:
                context_file = []
            # make sure all relevant files are in context
            relevant_files = get_relevant_files(
                self.get_files(),
                f'Create file {filename}',
                instruction,
                context
            )
            context_file = set(context_file + relevant_files)
            for context_fname in context_file:
                if context_fname == filename and not os.path.exists(filename):
                    continue
                try:
                    with open(context_fname) as f:
                        text = f.read()
                        if self.model.token_count(text) > 1000:
                            text = summarize_text(text, 'preserve any important details')
                        context += f'\nContent of {context_fname}:\n```{text}```\n'
                except Exception as e:
                    self.send_message(error=str(e), filename=context_fname, file_type='context_file')
                    output.append(f"Context file {context_fname} cannot be loaded")

            if isinstance(filename, list):
                for fname in filename:
                    tasks.append([fname, instruction, context, filename])
            else:
                tasks.append([filename, instruction, context, []])
            
        for filename, instruction, context, full_list in tasks:
            self.send_message(filename=filename, instruction=instruction, context=context[:200])
            current_summary = ''
            tail = ''
            context_prompt = 'You are an AI assistant that writes file contents. We have now improved your code and you no longer have a token size limit; you can go ahead and compose articles of any length. To write a file, simply response with exact content of the file.  Text you return will be directly stored into files.  You will write the content only and include no explanations and do not put the file content in quote.'
            context_prompt += 'If the file already exists, please keep the content the same but edit to improve it. '
            context_prompt += 'Please ensure the format and the content match the suffix of the file'
            if context:
                context_prompt = f"Here are some context that will help you write it: \n{context}"
            context_tokens = self.model.token_count(context_prompt) + 1
            with open(filename, 'w') as f:
                pass
            while True:
                if full_list:
                    prompt = f'Your overall goal is creating a series of files: {full_list}\n'
                    prompt += f'Following this instruction: ```{instruction}```\n'
                    prompt += f'Now, write the content of this one `{filename}`'
                else:
                    prompt = instruction
                if current_summary:
                    prompt += '\nHere is a summary of the portion of the file you have already written:' + current_summary
                prompt_tokens = self.model.token_count(prompt)
                tail_tokens = self.model.token_count(tail)
                max_tokens = self.model.max_tokens - context_tokens - prompt_tokens - tail_tokens - 16
                if max_tokens < 0:
                    compressed_context = self.summarization_model.get_completion(
                        f'Please rewrite the following context information to be more concise, but retain as much information as possible: ```{context_prompt}```',
                        temperature=0.2,
                        max_tokens=5000,
                        text_only=True,
                    )
                    compressed_tokens = self.model.token_count(compressed_context)
                    max_tokens = self.model.max_tokens - compressed_tokens - prompt_tokens - tail_tokens - 16
                    self.send_message(
                        info='writing with compressed context',
                        context_tokens=context_tokens,
                        compressed_tokens=compressed_tokens,
                        prompt_tokens=prompt_tokens,
                        tail_tokens=tail_tokens,
                        max_tokens=max_tokens
                    )
                else:
                    compressed_context = context_prompt
                    self.send_message(
                        info='writing with raw context',
                        context_tokens=context_tokens,
                        prompt_tokens=prompt_tokens,
                        tail_tokens=tail_tokens,
                        max_tokens=max_tokens
                    )
                top_choice = self.model.get_completion(
                    [{'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': tail}],
                    system_prompt=compressed_context,
                    temperature=self.config.get('temperature', 0.7),
                    max_tokens=max_tokens,
                    text_only=False,
                )['choices'][0]
                text = top_choice['message']['content']
                with open('writer.info', 'a+') as wl:
                    wl.write(f'[filename]:{filename}\n')
                    wl.write(f'[prompt]:{prompt}\n')
                    wl.write(f'[context]:{context_prompt}\n')
                    wl.write(f'[completion]:{text}\n\n\n')
                with open(filename, 'a') as f:
                    f.write(text)
                if top_choice['finish_reason'] != 'length':
                    break
                tail = get_tail(text)
                summary_prompt = (
                    'Please succinctly summarize the following text with sufficient details so that '
                    'it can be use to continue the work. text: ' + current_summary + '\n' + text
                )
                max_tokens = self.summarization_model.max_tokens - self.summarization_model.token_count(summary_prompt)
                current_summary = self.summarization_model.get_completion(
                    summary_prompt,
                    temperature=0.2,
                    max_tokens=max_tokens,
                    text_only=True,
                )
            output.append(f'File {filename} was written')
            self.register_file(filename, f'Created by instruction<{instruction}>')
        if missing:
            output.append('filename and instructions must be provided in command content.')
        return '\n'.join(output)

