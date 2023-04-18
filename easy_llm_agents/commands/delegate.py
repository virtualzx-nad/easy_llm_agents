"""Delegate a hard job to a worker"""
import uuid

from ..conversation import LLMConversation
from .command import BaseCommand, handlers


class DelegateCommand(BaseCommand,
    command='delegate',
    essential=True,
    description=f'''Delegate a list of tasks to workers.  You should always try to divide your objective to smaller tasks before you delegate them to workers.  You need to provide sufficient context for workers, and repeat any relevant information mentioned or returned in previous commands.  You must provide filenames for the worker so they can save information to be reused later.
''',
    additional_context='''
`delegate` example:
<user>: user instruction: Send a love letter based on `template.txt` to each of pikglk's brothers through email
<assistant>: [
  {
    "command": "self_note",
    "summary": "Plan steps to achieve goal",
    "content": [
        "Find who are Pikglk's brothers",
        "Determine each brother's email addresses",
        "Compose a love letter for each brother based on template provided",
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
      "brother_emails.txt": "Each brothers' emails",
    },
    "context": "You are writing lover letters to each of Pikglk's brothers. To do that you need to determine who are his brothers and their emails."
  }
]
<user>: `delegete` returns: pikglk has two brothers, Kigklg(kigklg@email.com) and Gkigkl(gkigkl@email.com)
<assistant>: [
  {
    "command": "delegate",
    "summary": "Compose emails for each brother based on template",
    "content": {
      "instruction": [
        "Write a love letter for Kigklg and save to `kigklg.txt` based on the template in `template.txt`",
        "Write a love letter for Gkigkl and save to `gkigkl.txt` based on the template in `template.txt`"
      ]
    },
    "files": {
      "template.txt": "Template for the love letters",
      "kigklg.txt": "A love letter to Kigklg",
      "gkigkl.txt": "A love letter to Gkigkl"
    },
    "context": "You are writing lover letters based on a template to each of Pikglk's brothers, Kigklg and Gkigkl, to be sent through email."
  }
]
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
            context = entry.get('context', '')
            if not isinstance(context, list):
                context = [context]
            context_str = ''
            files = entry.get('files', {})
            for item in context:
                if isinstance(item, dict):
                    item = ', '.join(f'{key}:{value}' for key, value in item.items())
                else:
                    item = str(item)
                if item:
                    context_str += item + '\n'
            known_files = self.get_files()
            if files:
                context_str += '\nHere is a list of files, if one describes your output you should write to the file and if one describes information you need you should use that file:\n'
                if isinstance(files, dict):
                    for name, purpose in files.items():
                        context_str += f'  - {name}: {purpose}\n'
                        self.register_file(name, purpose)
                elif isinstance(files, list):
                    for file_info in files:
                        if 'filename' in file_info and 'description' in file_info:
                            context_str += f'  - {file_info["filename"]}: {file_info["description"]}\n'
                            self.register_file(file_info["filename"], file_info["description"])
                        elif file_info in known_files:
                            context_str += f'  - {file_info}: {known_files[file_info]}\n'
                        else:
                            context_str += f'  - {file_info}\n'
            else:  # caller forgot to specify what files are there.  we can fill the blank
                context_str += self.get_file_descriptions()
        instructions = [item for item in instructions if item]
        if not instructions:
            return 'You must provide `instruction` for the `delegate` command'
        num_tasks = len(instructions)
        self.send_message(num_tasks=num_tasks)
        results = []
        for i in range(num_tasks):
            results.append(self.do_task(i, instructions, context_str, results))
        return '\n'.join(f'Instruction `{instructions[i]}` returns: {item}' for i, item in enumerate(results))

    def do_task(self, index, instructions, context, prev_results):
        # task configuration
        worker_name = str(uuid.uuid4())[:8]
        instruction = instructions[index]
        fixed_instruction = 'You must report if you are successful with `answer`. It has to be a complete and standalone answer and does not refer to anything previously discussed. Anything that you are asked to answer or create must be provided either in answer directly, or in files which you explicitly name in answer.  You must specify filenames and variable names explicitly in the answer text. '
        escalation_level = [
            {'T': 0.3, 'extra_instruction': 'Do not delegate if your goal can be achieved with one single command.'},
            {'T': 0.5, 'extra_instruction': 'Be creative and break the problem into smaller and easier problems, then delegate them.'},
            {'T': 0.6, 'extra_instruction': 'Be creative and break the problem into smaller and easier problems, then delegate them.'},
            {'T': 0.9, 'extra_instruction': 'Break the problem into smaller tasks and delegate each.  If you cannot solve the problem, summarize your findings'}
        ]
        model = 'gpt-4'  # gpt 3.5 simply doesn't work

        self.send_message(name=worker_name, instruction=instruction, context=context)
        if len(instructions) > 1:
            context += 'This is one step in a series of tasks. '
            if index:
                context += 'Previous steps and results:\n'
                for prev_i, prev_r in zip(instructions, prev_results):
                    context += f'    {prev_i}: {prev_r}\n'
            if index < len(instructions) - 1:
                context += 'Steps after this one:\n'
                for next_i in instructions[index+1:]:
                    context += f'    {next_i}\n'
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
                system_prompt=context,
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
            prompt = instruction.strip() + '\n' + fixed_instruction + setting['extra_instruction']
            # self.send_message(name=worker_name, prompt=prompt, context=task['context'])
            try:
                answer = driver.send(prompt)
                self.send_message(name=worker_name, answer=answer)
            except Exception as e:
                print(f'Exception occured in worker: {e}')
                import traceback
                traceback.print_exc()
                # for entry in conv.history:
                #     print(f"{entry['role']}: {entry['content']}")
                continue
            # finally:
            return answer
        return 'Delegate failed. Provide an alternative or simplify task.'