"""Delegate a hard job to a worker"""
import uuid

from ..conversation import LLMConversation
from .command import BaseCommand, handlers


class DelegateCommand(BaseCommand,
    command='delegate',
    essential=True,
    description=f'''Delegate a task to a worker. This is necessary because you have a token limit which make it impossible to perform tasks that involve too many steps.  Any tasks that do not need long contexts and require multiple steps should be delegated.  Provide the following fields in content:
     - `instruction`: instruction for the worker. The worker will only see your problem description, but not any previous conversations.
     - `context':  any context information that the worker need to know to fulfill the instruction
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
      "context": "You are writing a book about Kuabpajib that have five chapters: Introduction, Basic Kuabpajib, Advanced Kuabpajib, Future of Kuabpajib, Conclusion"
    }
  }
]
<user>: `delegete` returns: Chapter is written to file kuabpajib.txt
'''
):
    def generate_prompt(self):
        worker_name = str(uuid.uuid4())[:8]
        if isinstance(self.content, list):
            content = self.content[0]
        else:
            content = self.content
        # if content.get('difficulty', '').lower() == 'high':
        model = 'gpt-4'  # gpt 3.5 simply doesn't work
        # else:
        #     model = 'gpt-3.5-turbo'
        instruction = content.get('instruction', '').strip()
        if not instruction:
            return 'You must provide `instruction` for the `delegate` command'
        fixed_instruction = 'You must report if you are successful with `answer`. It has to be a complete and standalone answer and does not refer to anything previously discussed.'
        escalation_level = [
            {'model': model, 'T': 0.3, 'extra_instruction': 'Do not delegate simple tasks that can be done by one command.'},
            {'model': model, 'T': 0.5, 'extra_instruction': 'Try to think about some creative solution first then try it out.'},
            {'model': 'gpt-4', 'T': 0.6, 'extra_instruction': 'Be creative and think about how to break the problem into smaller more manageable problems, then try to delegate them.'},
            {'model': 'gpt-4', 'T': 0.9, 'extra_instruction': 'Feel free to break the problem into smaller tasks and delegate each to workers.  If you cannot solve the problem, summarize your findings'}
        ]
        for i, setting in enumerate(escalation_level):
            # create a conversation for the subtask
            self.send_message(name=worker_name, level=i, setting=setting)
            conv = LLMConversation(
                model=setting['model'],
                model_options={'temperature': setting['T'], 'max_tokens': 600},
                system_prompt=content.get('context'),
                metadata=self.metadata,
            )
            self.metadata['delegation_conversation'] = conv
            messages = []
            driver = BaseCommand.get_driver(conv, messenger=lambda **x: messages.append(x), overseer=handlers.do_nothing, qa=handlers.do_nothing)
            prompt = instruction.strip() + '\n' + fixed_instruction + setting['extra_instruction']
            try:
                answer = driver.send(prompt)
                self.send_message(answer=answer)
            except Exception as e:
                print(f'Exception occured in delegate worker: {e}')
                import traceback
                traceback.print_exc()
                continue
            # finally:
            #     for entry in conv.history:
            #         print(f"{entry['role']}: {entry['content']}")
            return answer
        self.context[f'delegate_{worker_name}_messages'] = messages
        self.context[f'delegate_{worker_name}_conv'] = conv
        return 'Delegate worker is not able to finish the task. Please provide an alternative or simpler task.'