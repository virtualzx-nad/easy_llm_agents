"""OpenAI wrappers.  Dropped support for non-chat endpoint for now."""
import os
import uuid
import json
import time
import hashlib
from functools import partial

import openai

# removed caching for public version

if os.getenv('OPENAI_API_KEY'):
    openai.api_key = os.getenv('OPENAI_API_KEY')
LOG_FUNC = print

# These are the default options used in completion models or chat completion models
# explicit values will always be saved with each cache
DEFAULT_CHAT_OPTIONS = dict(
    temperature=0.2,
    top_p=1.0,
    max_tokens=2000,
    n=1,
    frequency_penalty=0.1,
    presence_penalty=0.1,  
)


def get_openai_completion(
    messages,
    model="gpt-3.5-turbo",
    system_prompt='',
    starts_with_assistant=False,   # Only relevant if you supply a list of text instead of objects
    text_only=False,               # returns text directly instead of the normal response object with choices
    **gpt_options
):
    """Perform completion or chat completion"""
    if isinstance(messages, str):
        # for single prompt, package in a message
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": messages}
        ]
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
    options = DEFAULT_CHAT_OPTIONS.copy()
    options.update(gpt_options)
    options['messages'] = messages
    try:
        response = openai.ChatCompletion.create(model=model, **options).to_dict()
    except openai.error.RateLimitError as e:
        print('RateLimitError from OpenAI.  Likely the model is overloaded.  Waiting 30s to retry. ')
        time.sleep(30)
        response = openai.ChatCompletion.create(model=model, **options).to_dict()
    except openai.error.Timeout as e:
        print('Timeout from OpenAI.  Likely service dis down.  Waiting 30s to retry. ')
        time.sleep(30)
        response = openai.ChatCompletion.create(model=model, **options).to_dict()
    except openai.error.APIError as e:
        print('APIError from OpenAI.  The server encountered problems.  Waiting 10s to retry. ')
        time.sleep(10)
        response = openai.ChatCompletion.create(model=model, **options).to_dict()
    except openai.error.APIConnectionError as e:
        print('APIConnectionError from OpenAI.  Connection was reset.  Waiting 10s to retry. ')
        time.sleep(10)
        response = openai.ChatCompletion.create(model=model, **options).to_dict()
        

    if text_only:
        return response['choices'][0]['message']['content']
    else:
        return response


def get_openai_edit(
    text,
    instruction,
    model="text-davinci-edit-001",
    text_only=False,
    **gpt_options
):
    """Edit code or text.  For now, not cached"""
    response = openai.Edit.create(
        model=model,
        input=text,
        instruction=instruction,
        **gpt_options
    ).to_dict()
    
    if text_only:
        return response['choices'][0]['text']
    else:
        return response
