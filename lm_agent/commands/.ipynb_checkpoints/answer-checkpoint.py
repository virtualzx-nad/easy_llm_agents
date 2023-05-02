"""Talk to flesh and blood and render any help possible"""
from .command import Command
from ..utils import SkipMissingDict


class AnswerCommand(Command,
    command='answer',
    essential=True,
    description='Response to the user. The actual text given to user should be in the content field as a string. If one approach requires information from the user, try an alternatively approach instead of asking the user for information if possible.',
#     example=[
#         {"role": "system", "content": "user instruction: the shortest war in history?"},
#         {"role": "assistant", "content": """[
#   {
#     "command": "self_note",
#     "content": ["I have knowledge about the shortest war before my training", "The user did not ask for recent events or information so I will utilize existing knowledge to answer the question"]
#   },
#   {
#     "command": "answer", "content": "The shortest war in history was the Anglo-Zanzibar War, which lasted for only 38 minutes on August 27, 1896."
#   }
# ]"""}]
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

