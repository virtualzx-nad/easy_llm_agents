"""Talk to yourself to help your thinking process"""
from .command import BaseCommand

class SelfNoteCommand(BaseCommand,
    command='self_note',
    essential=True,
    description='Note to yourself to plan your action and break difficult tasks into managable steps. Notes are invisible to others. Try to plan how to perform difficult tasks and obtain information with your commands instead of asking the user. Since this command has no direct effect for the user, each time you issue commands there should be at least one command that is not `self_note`.'
):
    def generate_prompt(self):
        self.send_message(thoughts=self.content)
