"""Ask questions to the human to gain more info and learn a thing or two"""
from .command import BaseCommand

class AskCommand(BaseCommand,
    command='ASK',
    description='Ask the users about their intention and private information not publicly available. '
                'Do not ask for information that is likely available from search, webpage or other sources available to you.',
):
    def generate_response_to_human(self):
        return self.content
