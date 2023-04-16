"""Talk to flesh and blood and render any help possible"""
from .command import BaseCommand
from ..utils import SkipMissingDict


class AnswerCommand(BaseCommand,
    command='answer',
    essential=True,
    description='Answer a question or report that a requested task has been successfully performed, when you are confident of the results.',
):
    def generate_response_to_human(self):
        if isinstance(self.content, list):
            content = self.content
        else:
            content = [self.content]
        items = []
        for entry in content:
            if isinstance(entry, str):
                entry = self.format_text(entry)
            else:
                entry = str(entry)
            if entry:
                items.append(entry)
        return '\n'.join(items) or self.summary

