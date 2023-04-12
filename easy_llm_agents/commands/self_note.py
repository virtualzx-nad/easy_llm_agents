"""Talk to yourself to help your thinking process"""
from .command import BaseCommand

class SelfNoteCommand(BaseCommand,
    command='self_note',
    description='Note to yourself to plan your action and break difficult tasks into managable steps. Notes are invisible to others. Try to plan how to perform difficult tasks and obtain information with your commands instead of asking the user. '
):
    def generate_prompt(self):
        self.send_message(thoughts=self.content)
