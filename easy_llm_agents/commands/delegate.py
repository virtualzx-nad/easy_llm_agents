"""Delegate a hard job to a worker"""
import uuid

from ..conversation import LLMConversation
from .command import BaseCommand, handlers


class DelegateCommand(BaseCommand,
    command='delegate',
    essential=True,
    description=f'''Delegate each task to a worker if you have 3 or more tasks. This is necessary because you have a token limit which make it impossible to perform tasks that involve too many steps.  Any tasks that do not need long contexts and require multiple steps should be delegated. You must divide tasks into smaller ones before you delegate them.  Provide the following fields in content:
     - `instruction`: instruction for the worker. The worker will only see your problem description, but not any previous conversations.
     - `context':  any context information that the worker need to know to fulfill the instruction.  You must explicitly specify any artifacts such as URL, filenames, resource names that are involved or as output.
''',
    additional_context='''
Another example:
<user>: write a book about kuabpajib and save to kuabpajib.txt
<agent>: [
  {
    "command": "self_note",
    "summary": "Divide the book into chapters",
    "content": ["Introduction", "Basic Kuabpajib", "Advanced Kuabpajib", "Future of Kuabpajib", "Conclusion"]
  },
  {
    "command": "delegate",
    "summary": "write the first chaper and save to file",
    "content": {
      "instruction": "Write chapter `Introduction` for book `Kuabpajib` and save to file `kuabpajib.txt`",
      "context": "You are writing a book about Kuabpajib that have five chapters: Introduction, Basic Kuabpajib, Advanced Kuabpajib, Future of Kuabpajib, Conclusion.  The book is saved to file `kuabpajib.txt`"
    }
  }
]
<user>: `delegete` returns: Chapter is written to file kuabpajib.txt
'''
):
    def message_pipe(self, *args, **kwargs):
        """Pipe delegate messages to main"""
        self.send_message(*args, **kwargs)
        
    def generate_prompt(self):
        worker_name = str(uuid.uuid4())[:8]
        if isinstance(self.content, list):
            content = self.content[0]
        else:
            content = self.content
        model = 'gpt-4'  # gpt 3.5 simply doesn't work
        instruction = content.get('instruction', '').strip()
        context = content.get('context')
        if not isinstance(context, list):
            context = [context]
        context_str = ''
        for entry in context:
            if isinstance(entry, dict):
                entry = ', '.join(f'{key}:{value}' for key, value in entry.items())
            else:
                entry = str(entry)
        context_str += entry + '\n'
        self.send_message(instruction=instruction, context=context_str)
        if not instruction:
            return 'You must provide `instruction` for the `delegate` command'
        fixed_instruction = 'You must report if you are successful with `answer`. It has to be a complete and standalone answer and does not refer to anything previously discussed.  You must specify the effects of your action, such as the name of files created or POST API calls, etc.'
        escalation_level = [
            {'T': 0.3, 'extra_instruction': 'Do not delegate if your goal can be achieved with 3 or less steps.'},
            {'T': 0.5, 'extra_instruction': 'Be creative and break the problem into smaller and easier problems, then delegate them.'},
            {'T': 0.6, 'extra_instruction': 'Be creative and break the problem into smaller and easier problems, then delegate them.'},
            {'T': 0.9, 'extra_instruction': 'Break the problem into smaller tasks and delegate each.  If you cannot solve the problem, summarize your findings'}
        ]
        for i, setting in enumerate(escalation_level):
            # create a conversation for the subtask
            self.send_message(name=worker_name, level=i, setting=setting)
            conv = LLMConversation(
                model=model,
                model_options={'temperature': setting['T'], 'max_tokens': 1200},
                system_prompt=context_str,
                metadata=self.metadata,
            )
            driver = BaseCommand.get_driver(conv, messenger=self.message_pipe, work_dir=self.metadata.get('work_dir')) #, overseer=handlers.do_nothing, qa=handlers.do_nothing)
            prompt = instruction.strip() + '\n' + fixed_instruction + setting['extra_instruction']
            try:
                answer = driver.send(prompt)
                self.send_message(answer=answer)
            except Exception as e:
                print(f'Exception occured in delegate worker: {e}')
                import traceback
                traceback.print_exc()
                for entry in conv.history:
                    print(f"{entry['role']}: {entry['content']}")
                continue
            # finally:
            return answer
        return 'Delegate worker is not able to finish the task. Please provide an alternative or simpler task.'