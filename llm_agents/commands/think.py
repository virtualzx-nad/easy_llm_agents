"""Talk to yourself to help your thinking process"""
from .command import BaseCommand

class ThinkCommand(BaseCommand,
    command='THINK',
    description='Reason with yourself to navigate through the thinking process.  The user cannot see what you put into a THINK command, so you have to make sure your final results that are meant for the user are instead in an ANSWER command.  If you received a difficult problem, break it down into smaller tasks then address them one by one.',
):
    def generate_prompt(self):
        self.send_message(thoughts=self.content)
