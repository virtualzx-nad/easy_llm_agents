"""Talk to flesh and blood and render any help possible"""
from .command import BaseCommand

class AnswerCommand(BaseCommand,
    command='answer',
    description='Answer a question or report that a requested task has been successfully performed, when you are confident of the results.',
):
    def generate_response_to_human(self):
        return self.content

