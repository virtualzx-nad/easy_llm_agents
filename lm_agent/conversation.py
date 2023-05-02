"""A conversation with a language model which that tracks the history and handles interactions

Will try to be as agnostic as possible when it comes to models
"""
import re
import json
from .models import CompletionModel
from .utils import summarize_text


class AnswerTruncated(Exception):
    """The response has hit token limit and has been truncated."""
    pass


class LMConversation(object):
    """An ongoing conversation with an LLM
    
    Example:
    >>> c = LLMConversation(ai_persona='the donald')
    >>> c.talk('how do i kick it up a notch')
    "Well, let me tell you, nobody knows how to kick it up a notch better than me. I've been doing it my whole life. The key is to be bold and take risks. Don't be afraid to speak your mind and stand up for what you believe in. And always remember, confidence is key. Believe in yourself and others will believe in you too."
    """
    default_config = {
    }

    default_options = {
        'max_tokens': 500,
    }

    def __init__(self,
        model='gpt-3.5-turbo',
        model_options=None,
        user_persona="",  # 
        ai_persona="",    # What role the AI should play as
        system_prompt="", 
        metadata=None,    # metadata attached to the conversation
        summarization_threshold=10,   # Perform summarization when history reaches this length
        summarization_tail=4,         # last few messages in history will not be summarized
        summarization_model=None,
        config=None,
    ):
        """Create a conversation with the LLM
        
        Args:
            system_prompt:  Background instruction to the system before conversation starts
            user_persona:   What role the user is.
            ai_persona:     Override the role the AI will talk as.
            summary:        Summary of previous conversations
            metadata:       Metadata relevant to the conversation such as user ID, time, session id, demographics etc comes here.
        """
        self.history = []
        self.raw_history = []
        if isinstance(model, CompletionModel):
            self.model = model
        else:
            self.model = CompletionModel.get(model)
        summarization_model = summarization_model or model
        if isinstance(summarization_model, CompletionModel):
            self.summarization_model = summarization_model
        else:
            self.summarization_model = CompletionModel.get(summarization_model)
        self.model_options = self.default_options.copy()
        if model_options:
            self.model_options.update(model_options)
        self.system_prompt = system_prompt or ''
        self.user_persona = user_persona
        self.ai_persona = ai_persona
        self.metadata = {} if metadata is None else metadata
        self.summary = []
        self.summarization_threshold = summarization_threshold
        self.summarization_tail = summarization_tail
        self.config = self.default_config.copy()
        if config:
            self.config.update(config)
        
    
    def talk(self, content, footnote=None, header=None, raise_if_truncated=False, lead='', as_role='user'):
        """Talk to the model and return the results
        
        Args:
            content:   Text of the utterance of the user
            footnote:  If present, a last system message before AI response that will not enter history

        Returns:
            The text response from the AI
        """
        if isinstance(content, list):
            if all(isinstance(item, dict) for item in content):
                self.history.extend(content)
                self.raw_history.extend(content)
            else:
                raise TypeError('If you suppply a list to talk, it has to be OpenAI message format')
        else:
            self.history.append({'role': as_role, 'content': content})
            self.raw_history.append({'role': as_role, 'content': content})
        system_prompt = self.system_prompt
        if self.user_persona:
            system_prompt += '\nThe user talking to you is ' + self.user_persona
        if self.ai_persona:
            system_prompt += '\nIn the entire conversation you act as ' + self.ai_persona + '\n Always speak in this role and never break character.\n'
        previous = self.summary + self.history
        if footnote:
            previous += [{'role': 'system', 'content': footnote}]
        if header:
            system_prompt += '\n' + header
        self._last_content = previous               # for debug only
        self._last_system_prompt = system_prompt    # for debug only
        self._last_header = header or ''
        self._last_footnote = str(footnote) or ''
        self.summarize()
        
        resp = self.model.get_completion(
            previous,
            system_prompt=system_prompt,
            lead=lead,
            text_only=False,
            **self.model_options
        )
        top_choice = resp['choices'][0]
        if top_choice['finish_reason'] == 'length' and raise_if_truncated:
            self.history.pop()
            raise AnswerTruncated('Answer exceeded token limit')
        answer = top_choice['message']['content']
        self.history.append({'role': 'assistant', 'content': answer})
        self.raw_history.append({'role': 'assistant', 'content': answer})
        return answer

    def to_dict(self):
        """Convert object to a dictionary"""
        doc = {}
        fields = [
            'history', 'symmary', 'system_prompt',
            'model', 'model_options',
            'user_persona', 'ai_persona',
            'metadata', 'raw_history',
        ]
        for field in fields:
            doc[field] = getattr(self, field, '')
        return doc

    def serialize(self, indent=2):
        """Convert the conversation into a JSON string"""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, doc):
        """Create an object from dictionary"""
        return cls(**doc)
    
    @classmethod
    def from_json(cls, json_str):
        """Reconstruct the conversation from JSON string"""
        return cls.from_dict(json.loads(json_str))
        
    def summarize(self):
        """Summarize the conversation"""
        model = self.summarization_model
        target_tokens = self.model.token_count(f'{self._last_header}\n{self._last_system_prompt}\n{self._last_content}\n{self._last_footnote}') + self.model_options.get('max_tokens', 500) + 8
        # print(f'Expected tokens: {target_tokens}   Max tokens: {self.model.max_tokens}')
        if len(self.history) <= self.summarization_tail + 1:
            return
        if len(self.history) >= self.summarization_threshold or target_tokens >= self.model.max_tokens:
            if len(self.history) - 2 == self.summarization_tail:
                tail = self.summarization_tail - 1
            else:
                tail = self.summarization_tail
            keep = []
            to_summarize = self.summary + self.history[:-tail]
            work_list = []
            instruction = 'Succinctly summarize commands and their response, keep information as places, names, URLs, date/time and figures'
            for i, entry in enumerate(to_summarize):
                if entry['role'] != 'user':
                    work_list.append(entry)
                if (i == len(to_summarize) - 1 or entry['role'] == 'user') and work_list:
                    if len(work_list) == 1:
                        keep += work_list
                    else:
                        combined = '\n'.join(f"{entry['role']}: {entry['content']}" for entry in work_list)
                        keep.append({'role': 'system', 'content': summarize_text(combined, instruction)})
                    work_list = []
                if entry['role'] == 'user':
                    keep.append(entry)
            self.history = self.history[-tail:]
            self.summary = keep

    def save_history(self, filename):
        """Store full conversation history to a target location"""
        system_prompt = self.system_prompt
        if self.user_persona:
            system_prompt += '\nThe user talking to you is ' + self.user_persona
        if self.ai_persona:
            system_prompt += '\nIn the entire conversation you act as ' + self.ai_persona + '\n Always speak in this role and never break character.\n'
        content = format_messages(self.raw_history, system_prompt, self.model.config, True)
        with open(filename, 'w+') as lf:
            lf.write(content)
    
    def show(self):
        """Print the history out"""
        print(format_messages(self.history, config=self.model.config))
    
def format_messages(history, system_prompt=None, config=None, cap=False):
    config = config or {}
    sep = config.get('sep', '\n')
    if 'roles_names' in config:
        role_names = config['role_names']
    else:
        roles = config.get('roles', ('Human', 'Assistant'))
        role_names = {'user': roles[0], 'assistant': roles[1]}
    system_name = role_names.get('system', 'System')
    if system_prompt:
        output = f'{sep}{system_name}: {system_prompt}\n'
    else:
        output = ''
    for entry in history:
        role = entry["role"]
        name = role_names.get(role, role)
        output += f'{sep}{name}: {entry["content"]}'
    if cap:
        output += sep
    return output
