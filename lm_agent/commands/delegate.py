"""Delegate a hard job to a worker"""
import os
import ast
import json
import uuid

from ..conversation import LMConversation
from ..utils import get_relevant_files
from ..models import CompletionModel
from .command import Command
from . import handlers


class DelegateCommand(Command,
    command='delegate',
    essential=True,
    description=f'''Delegate a list of tasks to workers. The content has `instruction`, `files` and `context` fields.  You should always try to divide your objective to smaller tasks before you delegate them to workers.  You need to be verbose and explicit in your instructions, provide sufficient context for workers, and repeat any relevant information mentioned or returned in previous commands.  Do not create separate steps to Each worker should save their own files. 
''',
    example=[
        {'role': 'user', 'content': "Send a love letter based on `template.txt` to each of pikglk's brothers through email"},
        {'role': 'assistant', 'content': """[
  {
    "command": "think",
    "summary": "Plan steps to achieve goal",
    "content": [
      "Find who are Pikglk's brothers",
      "Determine each brother's email addresses",
      "Compose a love letter for each brother based on template provided",
      "Send each love letter"
    ]
  },
  {
   "notes": ["Proceed with the first step of the plan"],
   "command": "delegate",
   "summary": "Find Pikglk's brothers and their emails",
   "content": {
     "instruction": [
       "Determine who are Pikglk's brothers and save to `brothers.txt`",
       "Find each brothers' email and save to `brother_emails.txt`"
    ],
     "files": {
       "brothers.txt": "A list of Pikglk's brothers",
       "brother_emails.txt": "Each brothers' emails",
     },
     "context": "You are writing lover letters to each of Pikglk's brothers. To do that you need to determine who are his brothers and their emails."
   }
 }
]"""},
        {'role': 'system', 'content': "`delegete` returns: pikglk has two brothers, Kigklg(kigklg@email.com) and Gkigkl(gkigkl@email.com)"},
        {'role': 'assistant', 'content': """[
  {
    "notes": ["First step succeeded. Proceed with the second step"],
    "command": "delegate",
    "summary": "Compose emails for each brother based on template",
    "content": {
      "instruction": [
        "Write a love letter for Kigklg and save to `kigklg.txt` based on the template in `template.txt`",
        "Write a love letter for Gkigkl and save to `gkigkl.txt` based on the template in `template.txt`"
      ],
      "files": {
        "template.txt": "Template for the love letters",
        "kigklg.txt": "A love letter to Kigklg",
        "gkigkl.txt": "A love letter to Gkigkl"
      },
      "context": "You are writing lover letters based on a template to each of Pikglk's brothers, Kigklg and Gkigkl, to be sent through email."
    }
  }
]"""}],
):
    config = {
        'model': None,
        'adjust_model': None,
        'max_tokens': 900,
        'save': False,
        'max_depth': 1
    }
    def get_message_pipe(self, name):
        def message_pipe(*args, **kwargs):
            """Pipe delegate messages to main"""
            self.send_message(worker_name=name,*args, **kwargs)
        return message_pipe
        
    def generate_prompt(self):
        if not isinstance(self.content, list):
            content = [self.content]
        elif isinstance(self.content[0], str):
            content = [{'instruction': self.content}]
        else:
            content = self.content
        tasks = []
        
        model = CompletionModel.get(self.config.get('model') or self.config['default_model'])
        for entry in content:
            # first extract all the contents
            if isinstance(entry, str):
                entry = {'instruction': entry}
            instructions = entry.get('instruction', [])
            if not isinstance(instructions, list):
                instructions = [instructions]
            context = entry.get('context', '')
            if not isinstance(context, list):
                context = [context]
            if len(instructions) > 1:
                instructions = self.combine_steps(instructions, '\n'.join(context))
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
            relevant_files = get_relevant_files(
                self.get_files(),
                self.summary,
                instructions,
                context_str,
            )
            processed = []
            if files:
                context_str += '\nHere is a list of files, if one describes your output you should write to the file and if one describes information you need you should use that file:\n'
                if isinstance(files, dict):
                    for name, purpose in files.items():
                        context_str += f'  - {name}: {purpose}\n'
                        self.register_file(name, purpose)
                        processed.append(name)
                elif isinstance(files, list):
                    for file_info in files:
                        if 'filename' in file_info and 'description' in file_info:
                            context_str += f'  - {file_info["filename"]}: {file_info["description"]} {"(To be created)" if not os.path.exists(file_info["filename"]) else ""}\n'
                            self.register_file(file_info["filename"], file_info["description"])
                            processed.append(file_info["filename"])
                        elif isinstance(file_info, str) and file_info in known_files:
                            context_str += f'  - {file_info}: {known_files[file_info]} {"(To be created)" if not os.path.exists(file_info) else ""}\n'
                            processed.append(file_info)
                        else:
                            context_str += f'  - {file_info} {"(To be created)" if not os.path.exists(file_info) else ""}\n'
                            processed.append(file_info)
            relevant_files = [name for name in relevant_files if name not in processed]
            if relevant_files and not files:
                context_str += '\nHere is a list of files, if one describes your output you should write to the file and if one describes information you need you should use that file:\n'
            for name in relevant_files:
                context_str += f'  - {name}: {known_files[name]}\n'

        instructions = [item for item in instructions if item]
        if not instructions:
            return 'You must provide `instruction` for the `delegate` command'
        num_tasks = len(instructions)
        self.send_message(num_tasks=num_tasks)
        results = []
        for i in range(num_tasks):
            results.append(self.do_task(i, instructions, context_str, results, model=model))
        return '\n'.join(f'Instruction `{instructions[i]}` returns: {item}' for i, item in enumerate(results))

    def do_task(self, index, instructions, context, prev_results, model):
        from ..agent import Agent
        # task configuration
        worker_name = str(uuid.uuid4())[:8]
        instruction = instructions[index]
        fixed_instruction = 'You must report if you are successful with `answer`. It has to be a complete and standalone answer and does not refer to anything previously discussed. Anything that you are asked to answer or create must be provided either in answer directly, or in files which you explicitly name in answer.  You must specify filenames and variable names explicitly in the answer text. If you have the information, provide a succinct summary of the information in answer even if it is requested to be saved to file.'
        escalation_level = [
            {'T': 0.3, 'extra_instruction': 'Do not delegate if your goal can be achieved with one single command.'},
            {'T': 0.5, 'extra_instruction': 'Be creative and break the problem into smaller and easier problems, then delegate them.'},
            {'T': 0.6, 'extra_instruction': 'Be creative and break the problem into smaller and easier problems, then delegate them.'},
            {'T': 0.9, 'extra_instruction': 'Break the problem into smaller tasks and delegate each.  If you cannot solve the problem, summarize your findings'}
        ]

        self.send_message(name=worker_name, instruction=instruction, context=context)
        if len(instructions) > 1:
            context += 'This is one step in a series of tasks. '
            if index:
                context += 'For context, previous steps and results:\n'
                for prev_i, prev_r in zip(instructions, prev_results):
                    context += f'    {prev_i}: {prev_r}\n'
            if index < len(instructions) - 1:
                context += 'Steps after this one (that you will not do):\n'
                for next_i in instructions[index+1:]:
                    context += f'    {next_i}\n'
            context += 'Do not perform tasks that are assigned to other workers\n'
        for i, setting in enumerate(escalation_level):
            # create a conversation for the subtask
            if i:
                self.send_message(name=worker_name, level=i, setting=setting)
            stack = self.stack + [self]
            disable = self.config.get('disable') or []
            if len(stack) + 1 >= self.config.get('max_depth', 1):
                disable = list(disable) + [self.command]
            else:
                disable = list(disable)
            log_file = self.config['save']
            if not isinstance(log_file, str):
                if log_file:
                    log_file = f'{worker_name}.log'
                else:
                    log_file = None
            agent = Agent(
                model=model,
                metadata=self.metadata,
                system_prompt=context,
                messenger=self.get_message_pipe(worker_name),
                work_dir=self.work_dir,
                essential_only=False,
                overseer=handlers.do_nothing,
                log_file=log_file,
                config=self.config['parent_config'],
                disable=disable,
                stack=stack,
                model_options={'temperature': setting['T'], 'max_tokens': self.config['max_tokens']},
            )
            prompt = str(instruction).strip() + '\n' + fixed_instruction + setting['extra_instruction']
            # self.send_message(name=worker_name, prompt=prompt, context=task['context'])
            try:
                answer = agent.instruct(prompt)
                self.send_message(name=worker_name, answer=answer)
            except Exception as e:
                print(f'Exception occured in worker: {e}')
                import traceback
                traceback.print_exc()
                # for entry in conv.history:
                #     print(f"{entry['role']}: {entry['content']}")
                continue
            finally:
                filename = os.path.abspath(os.path.join(self.work_dir, f'{worker_name}.log'))
                agent.conversation.save_history(filename)
            return answer
        return 'Delegate failed. Provide an alternative or simplify task.'
    
    def combine_steps(self, steps, context):
        """The agent sometimes overly divide the tasks.  regroup them properly here"""
        prompt = f"""You will be given a list of tasks. You will group them to be assigned to workers.

If results of a task need to be saved to a file, it have to be done by the same worker.  This is because workers can write files or read files other workers created, but they cannot pass large amount of information between them outside of files.  As such, one worker cannot save the output of another worker to a file.   Saving files should never be a separate task.  You should not group any tasks together unless for this particular reason.

Note that small amount of information that can be fitted within a single sentence can be passed between workers and do not need to be saved to files.

On the other hand, some tasks can be partitioned into parallel tasks that can be performed by multiple workers.   If tasks can be divided on many levels, do the division on the highest level only.

Please divide the tasks into groups so that each group can be performed by a separate worker and data transfer between workers is minimized.

First discuss how tasks should be separated and grouped in a comment block.
At the end of the comment, note that if the groups discussed in the comments are complete, and if not so make sure you use the complete list.

Then write one Python list, each entry is a string that  combines all tasks for one group of tasks.  It must contain all groups no matter how many groups there are. Do not provide any explanations or descriptions.  Always return the entire list and make no omission.  The list must be directly evaluable in Python.  Do not simplify or summarize any information in the task.  Keep all details, instructions and filenames.

Example:
'''
Tasks:
  - read technical design `design.doc`
  - based on this create module `a` with functions `a1`, `a2`, module `b` and module `c` with functions `c1`, `c2` and `c3`
  - save each module to file in the form of x.py
Returns this
# Creation of each module is an isolated task that should be separated.
# Creation of functions should not be separated because they are deeper level
# The creation of modules and saving to file need to be grouped together
# Group 1: Create module `a` with functions `a1` and `a2` and save to `a.py`
# Group 2: Create module `b` and save to `b.py`
# Group 3: Create module `c` with functions `c1`, `c2` and `c3` and save to `c.py`
```python
[
  "Create module `a` with functions `a1` and `a2` based on technical design in `design.doc` and save it to file `a.py`",
  "Create module `b` based on technical design in `design.doc` and and save it to file `b.py`",
  "Create module `c` with functions `c1`, `c2` and `c3` based on technical design in `design.doc` and and save it to file `c.py`"
]
```
'''

Here are some context for those tasks to help you better perform the grouping:  ```{context}```

Tasks:\n"""
        for step in steps:
            prompt += f'  - {step}\n'
        model = CompletionModel.get(self.config.get('adjust_model') or self.config['default_model'])
        response = model.get_completion(prompt, temperature=0.2, text_only=True)
        start = response.find('[')
        end = response.rfind(']') + 1
        if start < 0 or end < start:
            return steps
        response = response[start:end]
        try:
            result = ast.literal_eval(response)
        except Exception:
            try:
                result = json.loads(response)
            except Exception as e:
                print('Exception occured when trying to repartition delegate tasks: ', e)
                print(response)
                result = steps
        if steps != result:
            print(f'Restructure delegate steps: {steps} => {result}')
        else:
            print('Restructure did not change steps')
        return result
