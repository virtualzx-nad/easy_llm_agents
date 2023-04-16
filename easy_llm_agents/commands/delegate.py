"""Delegate a hard job to a worker"""
import uuid

from ..conversation import LLMConversation
from .command import BaseCommand, handlers


class DelegateCommand(BaseCommand,
    command='delegate',
    essential=True,
    description=f'''Delegate a list of tasks to workers.  You should always try to divide your objective to smaller tasks before you delegate them to workers.  Workers can only see their instruction and cannot see past conversations, so you need to provide sufficient context for them.   Provide the following fields in content:
     - `instruction`: list of instructions.  Each worker will be given one instruction.
     - `context':  any context information that the workers need to know to fulfill the instruction.  You must explicitly specify any artifacts such as URL, filenames, resource names that are involved or as output.  Workers answering the same command see the same context, but workers answering different commands cannot see each others' contexts.
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
    "summary": "write individual chapters of `Kuabpajib` and save to file",
    "content": {
      "instruction": ["Write chapter `Introduction`", "Write chapter `Basic Kuabpajib`", "Write chapter `Advanced Kuabpajib`", "Write chapter `Future of Kuabpajib`", "Write chapter `Conclusion`"],
      "context": "You are writing a book about Kuabpajib that have five chapters: Introduction, Basic Kuabpajib, Advanced Kuabpajib, Future of Kuabpajib, Conclusion.  The book is saved to file `kuabpajib.txt`"
    }
  }
]
<user>: `delegete` returns: The first two chapters are saved to file kuabpajib.txt
'''
):
    def get_message_pipe(self, name):
        def message_pipe(*args, **kwargs):
            """Pipe delegate messages to main"""
            self.send_message(worker_name=name, *args, **kwargs)
        return message_pipe
        
    def generate_prompt(self):
        if not isinstance(self.content, list):
            content = [self.content]
        else:
            content = self.content
        tasks = []
        for entry in content:
            # first extract all the contents
            worker_name = str(uuid.uuid4())[:8]
            instructions = entry.get('instruction', [])
            if not isinstance(instructions, list):
                instructions = [instructions]
            context = entry.get('context')
            if not isinstance(context, list):
                context = [context]
            context_str = ''
            for item in context:
                if isinstance(item, dict):
                    item = ', '.join(f'{key}:{value}' for key, value in item.items())
                else:
                    item = str(item)
                context_str += item + '\n'
            for item in instructions:
                if not item:
                    continue
                tasks.append(dict(instruction=item, context=context_str))
        self.send_message(num_tasks=len(tasks))
        if not tasks:
            return 'You must provide `instruction` for the `delegate` command'
        result = ''
        for i, task in enumerate(tasks):
            if len(task) > 1:
                result += f'Instruction `{task["instruction"]}` returns: '
            result += self.do_task(task) + '\n'
        return result

    def do_task(self, task):
        # task configuration
        worker_name = str(uuid.uuid4())[:8]
        fixed_instruction = 'You must report if you are successful with `answer`. It has to be a complete and standalone answer and does not refer to anything previously discussed. Anything that you are asked to answer or create must be provided either in answer directly, or in files which you explicitly name in answer.  You must specify filenames and variable names explicitly in the answer text. '
        escalation_level = [
            {'T': 0.3, 'extra_instruction': 'Do not delegate if your goal can be achieved with 3 or less steps.'},
            {'T': 0.5, 'extra_instruction': 'Be creative and break the problem into smaller and easier problems, then delegate them.'},
            {'T': 0.6, 'extra_instruction': 'Be creative and break the problem into smaller and easier problems, then delegate them.'},
            {'T': 0.9, 'extra_instruction': 'Break the problem into smaller tasks and delegate each.  If you cannot solve the problem, summarize your findings'}
        ]
        model = 'gpt-4'  # gpt 3.5 simply doesn't work

        self.send_message(name=worker_name, **task)
        for i, setting in enumerate(escalation_level):
            # create a conversation for the subtask
            self.send_message(name=worker_name, level=i, setting=setting)
            conv = LLMConversation(
                model=model,
                model_options={'temperature': setting['T'], 'max_tokens': 1200},
                system_prompt=task['context'],
                metadata=self.metadata,
            )
            driver = BaseCommand.get_driver(conv, messenger=self.get_message_pipe(worker_name), work_dir=self.metadata.get('work_dir')) #, overseer=handlers.do_nothing, qa=handlers.do_nothing)
            prompt = task['instruction'].strip() + '\n' + fixed_instruction + setting['extra_instruction']
            # self.send_message(name=worker_name, prompt=prompt, context=task['context'])
            try:
                answer = driver.send(prompt)
                self.send_message(name=worker_name, answer=answer)
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