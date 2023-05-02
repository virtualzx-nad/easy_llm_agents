"""OpenAI wrappers.  Dropped support for non-chat endpoint for now."""
import os
import time

import openai
import tiktoken

from .model import CompletionModel




class OpenAIModel(CompletionModel):
    """Generic class for all OpenAI completion models"""
    default_options = dict(
        temperature=0.2,
        top_p=1.0,
        max_tokens=2000,
        n=1,
        frequency_penalty=0.1,
        presence_penalty=0.1,  
    )
    
    _usage_data = {'total_cost': 0}

    def initialize(self):
        if 'openai_api_key' in self.config:
            openai.api_key = self.config['openai_api_key']
        elif os.getenv('OPENAI_API_KEY'):
            openai.api_key = os.getenv('OPENAI_API_KEY')
        if self.name:
            encoding = tiktoken.encoding_for_model(self.name)
        return {'encoding': encoding, 'openai_api_key': openai.api_key}

    def get_completion(
        self,
        messages,
        system_prompt='',
        text_only=False,               # returns text directly instead of the normal response object with choices
        lead='',                       # Force agent to start its answer with this string
        callback=None,
        **model_options
    ):
        """Perform completion or chat completion"""
        if isinstance(messages, str):
            # for single prompt, package in a message
            messages = [{"role": "user", "content": messages}]
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages

        elif messages and isinstance(messages, (list, tuple)):
            if isinstance(messages[0], str):
                messages = [system_prompt] + messages
                messages = [
                    {
                        "role": 
                            "system" if not i
                                else (
                                    "user" if (i + int(starts_with_assistant)) % 2 else "assistant"
                                ),
                        "content": entry,
                    }
                    for (i, entry) in enumerate(messages)
                ]
            else:
                messages = [{"role": "system", "content": system_prompt}] + messages
        options = self.model_options.copy()
        if model_options:
            options.update(model_options)
        options['messages'] = messages
        self._last_messages = messages.copy()
        tokens = self.token_count(messages)
        actual_max = self.max_tokens - tokens - 8
        if actual_max < 0:
            raise RuntimeError('Incoming prompt is larger than model token limit')
        if actual_max < options['max_tokens']:
            if options['max_tokens'] - actual_max > 300:
                print(f"Shrinking max_token from {options['max_tokens']} to {actual_max}")
            options['max_tokens'] = actual_max
        try:
            response = openai.ChatCompletion.create(model=self.name, **options).to_dict()
        except openai.error.RateLimitError as e:
            print('RateLimitError from OpenAI.  Likely the model is overloaded.  Waiting 30s to retry. ')
            time.sleep(30)
            response = openai.ChatCompletion.create(model=self.name, **options).to_dict()
        except openai.error.Timeout as e:
            print('Timeout from OpenAI.  Likely service dis down.  Waiting 30s to retry. ')
            time.sleep(30)
            response = openai.ChatCompletion.create(model=self.name, **options).to_dict()
        except openai.error.APIError as e:
            print('APIError from OpenAI.  The server encountered problems.  Waiting 10s to retry. ')
            time.sleep(10)
            response = openai.ChatCompletion.create(model=self.name, **options).to_dict()
        except openai.error.APIConnectionError as e:
            print('APIConnectionError from OpenAI.  Connection was reset.  Waiting 10s to retry. ')
            time.sleep(10)
            response = openai.ChatCompletion.create(model=self.name, **options).to_dict()
        for usage, count in response['usage'].items():
            self._usage_data['total_cost'] += self.pricing.get(usage, 0) * count
    
        if text_only:
            result = response['choices'][0]['message']['content']
            return result
        else:
            return response

    def token_count(self, text):
        if not self.model_data:
            raise NotImplemented(f'Encoding count is not available for {type(self)}({self.name})')
        encoding = self.model_data['encoding']
        if isinstance(text, str):
            return len(encoding.encode(text))
        elif isinstance(text, list) and text and isinstance(text[0], dict):
            messages = text
            num_tokens = 0
            for message in messages:
                num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                for key, value in message.items():
                    num_tokens += len(encoding.encode(value))
                    if key == "name":  # if there's a name, the role is omitted
                        num_tokens += -1  # role is always required and always 1 token
            num_tokens += 2  # every reply is primed with <im_start>assistant
            return num_tokens
        else:
            raise RuntimeError('unrecognized message structure')

    @classmethod
    def total_cost(cls):
        """Report total OpenAI cost"""
        return cls._usage_data['total_cost']

class GPT35(OpenAIModel, name='gpt-3.5-turbo', max_tokens=4000):
    pricing = {
        "total_tokens": 0.002/1000,
    }

class GPT4(OpenAIModel, name='gpt-4', max_tokens=8000):
    pricing = {
        "completion_tokens": 0.06/1000,
        "prompt_tokens": 0.03/1000,
    }
