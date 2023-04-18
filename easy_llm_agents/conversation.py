"""A conversation with a language model which that tracks the history and handles interactions

Will try to be as agnostic as possible when it comes to models but I can only test against OpenAI for now
"""
import json
from .clients import get_completion
from .utils import token_count


class AnswerTruncated(Exception):
    """The response has hit token limit and has been truncated."""
    pass

class LLMConversation(object):
    """An ongoing conversation with an LLM
    
    Example:
    >>> c = LLMConversation(ai_persona='the donald')
    >>> c.talk('how do i kick it up a notch')
    "Well, let me tell you, nobody knows how to kick it up a notch better than me. I've been doing it my whole life. The key is to be bold and take risks. Don't be afraid to speak your mind and stand up for what you believe in. And always remember, confidence is key. Believe in yourself and others will believe in you too."
    """
    def __init__(self,
        model='gpt-3.5-turbo', model_options=None,
        user_persona="",  # 
        ai_persona="",    # What role the AI should play as
        summary='',       # summary of previous conversations
        system_prompt="", 
        metadata=None,    # metadata attached to the conversation
        summarization_threshold=10,   # Perform summarization when history reaches this length
        summarization_tail=4,         # last few messages in history will not be summarized
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
        self.model = model
        self.model_options = model_options or {}
        self.system_prompt = system_prompt or ''
        self.user_persona = user_persona
        self.ai_persona = ai_persona
        self.metadata = metadata or {}
        self.summary = summary
        self.summarization_threshold = summarization_threshold
        self.summarization_tail = summarization_tail
        
    
    def talk(self, content, footnote=None, raise_if_truncated=False):
        """Talk to the model and return the results
        
        Args:
            content:   Text of the utterance of the user
            footnote:  If present, a last system message before AI response that will not enter history

        Returns:
            The text response from the AI
        """
        self.history.append({'role': 'user', 'content': content})
        system_prompt = self.system_prompt
        if self.user_persona:
            system_prompt += '\nThe user talking to you is ' + self.user_persona
        if self.ai_persona:
            system_prompt += '\nIn the entire conversation you act as ' + self.ai_persona + '\n Always speak in this role and never break character.\n'
        if self.summary:
            system_prompt += '\nSummary of previous conversations:\n' + self.summary
        previous = list(self.history)
        if footnote:
            previous += [{'role': 'system', 'content': footnote}]

        self._last_content = previous               # for debug only
        self._last_system_prompt = system_prompt    # for debug only

        resp = get_completion(
            previous,
            model=self.model,
            system_prompt=system_prompt,
            text_only=False,
            **self.model_options
        )
        top_choice = resp['choices'][0]
        if top_choice['finish_reason'] == 'length' and raise_if_truncated:
            self.history.pop()
            raise AnswerTruncated('Answer exceeded token limit')
        answer = top_choice['message']['content']
        self.history.append({'role': 'assistant', 'content': answer})
        self.summarize()
        return answer

    def to_dict(self):
        """Convert object to a dictionary"""
        doc = {}
        fields = [
            'history', 'symmary', 'system_prompt',
            'model', 'model_options',
            'user_persona', 'ai_persona',
            'metadata',
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
        if len(self.history) > self.summarization_threshold:
            to_summarize = '\n'.join(
                f'{entry["role"]}: {entry["content"]}'
                for entry in self.history[:-self.summarization_tail]
            )
            if self.summary:
                current_summary = f"Summary of earlier exchanges: ```{self.summary}```"
            else:
                current_summary = ''
            prompt = f"""This is a series of exchanges between a user and an assistant which shall be referred to as "the assistant",  which issues commands in JSON format.   Please extract any information that will be helpful for later conversations.  Make sure all user questions and requirements are present.  Keep all filenames and their descriptions.\n{current_summary}\nExchanges: ```{to_summarize}```"""
            if token_count(prompt, 'gpt-3.5-turbo') < 2500:
                model = 'gpt-3.5-turbo'
            else:
                model = 'gpt-4'
            self.summary = get_completion(prompt, model=model, temperature=0.2, max_tokens=1500, text_only=True)
            self.history = self.history[-self.summarization_tail:]
