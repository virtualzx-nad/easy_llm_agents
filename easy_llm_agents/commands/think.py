"""Talk to yourself to help your thinking process"""
from .command import BaseCommand

class ThinkCommand(BaseCommand,
    command='THINK',
    description='Talk to yourself to plan your action and break difficult tasks into managable steps. THINK command is invisible to user. Do not ask how to perform a task, THINK about a plan yourself. Do not ask for information; use your command to obtain them. '
):
    def generate_prompt(self):
        self.send_message(thoughts=self.content)
