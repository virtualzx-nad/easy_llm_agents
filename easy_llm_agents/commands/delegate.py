"""Delegate a hard job to a worker"""
import uuid

from ..conversation import LLMConversation
from .command import BaseCommand, handlers


class DelegateCommand(BaseCommand,
    command='delegate',
    essential=True,
    description=f'''Delegate a list of tasks to workers.  You should always try to divide your objective to smaller tasks before you delegate them to workers.  Workers can only see their instruction and cannot see past conversations, so you need to provide sufficient context for them.  You MUST supply all relevant filenames, otherwise workers do not know of those files.
''',
    additional_context='''
Another example:
<user>: Send a love letter to each of pikglk's brothers through email
<agent>: [
  {
    "command": "self_note",
    "summary": "Plan steps to achieve goal",
    "content": [
        "Find who are Pikglk's brothers",
        "Determine each brother's email addresses",
        "Compose a love letter for each brother",
        "Send each love letter"
    ]
  },
  {
    "command": "delegate",
    "summary": "Find Pikglk's brothers and their emails",
    "content": {
      "instruction": [
        "Determine who are Pikglk's brothers and save to `brothers.txt`",
        "Find each brothers' email and save to `brother_emails.txt`"
      ]
    },
    "files": {
      "brothers.txt": "A list of Pikglk's brothers",
      "brother_emails.txt": "Each brothers' emails"
    }
  }
]
<user>: `delegete` returns: pikglk has two brothers, Kigklg(kigklg@email.com) and Gkigkl(gkigkl@email.com)
<assistant>: [
  {
    "command": "delegate",
    "summary": "Compose emails for each brother",
    "content": {
      "instruction": [
        "Write a love letter for Kigklg and save to `kigklg.txt`",
        "Write a love letter for Gkigkl and save to `gkigkl.txt`"
      ]
    },
    "files": {
      "kigklg.txt": "A love letter to Kigklg",
      "gkigkl.txt": "A love letter to Gkigkl"
    }
  }
]

Ask workers to create files as their output.  Do not create separate steps to save files as workers can only communicate through files. 
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
            instructions = entry.get('instruction', [])
            if not isinstance(instructions, list):
                instructions = [instructions]
            context = entry.get('context')
            if not isinstance(context, list):
                context = [context]
            context_str = ''
            files = entry.get('files', {})
            for item in context:
                if isinstance(item, dict):
                    item = ', '.join(f'{key}:{value}' for key, value in item.items())
                else:
                    item = str(item)
                context_str += item + '\n'
            if files:
                context_str += '\nHere is a list of files, if one describes your output you should write to the file and if one describes information you need you should use that file:\n'
                if isinstance(files, dict):
                    for name, purpose in files.items():
                        context_str += f'  - {name}: {purpose}\n'
                elif isinstance(files, list):
                    for file_info in files:
                        if 'filename' in file_info and 'description' in file_info:
                            context_str += f'  - {file_info["filename"]}: {file_info["description"]}\n'
                        else:
                            context_str += f'  - {file_info}\n'
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
            {'T': 0.3, 'extra_instruction': 'Do not delegate if your goal can be achieved with one single command.'},
            {'T': 0.5, 'extra_instruction': 'Be creative and break the problem into smaller and easier problems, then delegate them.'},
            {'T': 0.6, 'extra_instruction': 'Be creative and break the problem into smaller and easier problems, then delegate them.'},
            {'T': 0.9, 'extra_instruction': 'Break the problem into smaller tasks and delegate each.  If you cannot solve the problem, summarize your findings'}
        ]
        model = 'gpt-4'  # gpt 3.5 simply doesn't work

        self.send_message(name=worker_name, **task)
        for i, setting in enumerate(escalation_level):
            # create a conversation for the subtask
            if i:
                self.send_message(name=worker_name, level=i, setting=setting)
            stack = self.stack + [self]
            if len(stack) > 2:
                disable = [self.command]
            else:
                disable = []
            conv = BaseCommand.create_conversation(
                model='gpt-4',
                metadata=self.metadata,
                model_options={'temperature': setting['T'], 'max_tokens': 1200},
                system_prompt=task['context'],
                disable=disable,
                essential_only=False,
            )
            driver = BaseCommand.get_driver(
                conv,
                messenger=self.get_message_pipe(worker_name),
                work_dir=self.metadata.get('work_dir'),
                essential_only=False,
                overseer=handlers.do_nothing,
                qa=handlers.do_nothing,
                log_file=f'{worker_name}.log',
                disable=disable,
                stack=stack,
            )
            prompt = task['instruction'].strip() + '\n' + fixed_instruction + setting['extra_instruction']
            # self.send_message(name=worker_name, prompt=prompt, context=task['context'])
            try:
                answer = driver.send(prompt)
                self.send_message(name=worker_name, answer=answer)
            except Exception as e:
                print(f'Exception occured in delegate worker: {e}')
                import traceback
                traceback.print_exc()
                # for entry in conv.history:
                #     print(f"{entry['role']}: {entry['content']}")
                continue
            # finally:
            return answer
        return 'Delegate worker is not able to finish the task. Please provide an alternative or simpler task.'