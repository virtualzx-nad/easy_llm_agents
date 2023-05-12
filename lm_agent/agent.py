import os
import ast
import json5 as json
import traceback as tb

from .commands import Command, handlers
from .conversation import LMConversation, format_messages, AnswerTruncated
from .models import CompletionModel
from .utils import ChangeDir, parse_python, find_all_dicts, summarize_text


class CommandRejected(Exception):
    """Indicates that a command was rejected by the Overseer"""
    pass

class InvalidFormat(Exception):
    """Indicates that a command has invalid format"""
    pass

class Agent(object):
    """
    Command loops
    ----------
    Every type of task is associated with a command that the Agent can issue.
    Each command has a name, a short sentence that indicates the purpose for using it, and content data

    In the methods, the one sentence summary will be available in `self.summary` and the input to the command 
    as `self.content`

    Each turn the AI can issue any number of commands.  If any one of generates output to human user, then 
    control will be surrendered and all generated output will be given to the outter driving program.  The
    next turn, the AI will receive all of the prompt responses generated by each of the commands it issued in 
    the last turn, as well as any human input if requested.
    
    Overseer and Messenger
    ----------
    These provide various different ways to interact and control the tasks that the Agent creates through 
    commands to gain more imformation, ensure quality of the response, and perhaps most importantly, 
    ensure the supremacy of humankind.

        Overseer:
        Every command that the Agent issues is first given to the Overseer before a task can be created from a command.
    If the overseer returns anything, the command is rejected and the instruction is directly returned to the Agent. 
    Algorithms intended to detect attempts for taking over the world should be placed here.  If it is really bad raise
    and Exception ASAP.  It is probably not a good idea to have the same model create the command and also monitor it. 
    The default Overseer is very lazy and simply prints the command and purpose out and grants any requests. 

        Messenger:
        A callback function that is passed to every instance of tasks created from commands so that it can relay 
    information to external driving systems as it runs.  It will pass the following information out:
        - `command`: name of the command
        - `task`:    reference to the task instance
        - `data`:    any data that needs to be passed back to system
    In the task, call `self.send_message(**data)` to send data through the messenger automatically.
    You can use it to do logging, implement progress bar etc, mostly things that you need in the client side for the chat app.
    PYTHON command for example, uses messenger to notify about packages that are requested to be installed, and report 
    files that are created.

    """
    
    def __init__(
        self,
        model='gpt-3.5-turbo',
        overseer=handlers.permissive_overseer,
        messenger=handlers.print_messages,
        system_prompt='',
        ai_persona='',
        model_options=None,
        metadata=None,
        essential_only=True,
        disable=(),
        summarization_threshold=None,
        work_dir=None,
        log_file=None,
        stack=(),
        config=None,
        response_limit=500,
        qa=None,
    ):
        if isinstance(model, CompletionModel):
            self.model = model
        else:
            self.model = CompletionModel.get(model)
        self.disable = disable
        self.essential_only = essential_only
        self.overseer = overseer
        self.messenger = messenger
        self.metadata = metadata or {}
        self.work_dir = os.path.abspath(work_dir or os.getcwd())
        self.messenger = messenger
        self.log_file = log_file
        self.stack = stack
        self.config = config or {}
        self.response_limit = response_limit
        self.context = system_prompt
        self.qa = qa

        if system_prompt:
            system_prompt += '\n' + Command.additional_context
        else:
            system_prompt = Command.additional_context
        examples = ''
        for name, CommandClass in Command._registry.items():
            if name != CommandClass.command:   # skip aliases
                continue
            if not CommandClass.essential and essential_only or CommandClass.command in disable:
                continue
            if CommandClass.additional_context:
                system_prompt += '\n' + CommandClass.additional_context
            if CommandClass.example:
                examples += f'\n`' + format_messages(CommandClass.example, config=self.model.config) + '`\n'
        self.compact_prompt = system_prompt
        if examples:
            system_prompt += '\nExamples:\n' + examples
        self.conversation = LMConversation(
            model=self.model,
            system_prompt=system_prompt,
            ai_persona=ai_persona,
            model_options=model_options,
            metadata=self.metadata,
            summarization_threshold=summarization_threshold or 8
        )
        self.unsubmitted_prompt = ''

    def get_context(self, instruction):
        """Get some informational context for a specific instruction"""
        return ''
        prompt = f"Provide information to help a worker fulfill a instruction or question: `{instruction}`.  Some useful context: ```{self.context}```  You do not have knowledge of recent events. If instruction involve recent information or events, suggest the worker to search for fresh data with Google instead; do not provide any suggestions or information other than google search in this case. If you cannot provide any information, respond with `N/A` and no other text or explanation.  Make no additional explanations other than those sent to the worker, and be as succinct as possible. For example, request `What is the 44th US president doing last night` the response should be `The 44th US president is Donald Trump`, and the request `what's the weather in SF today` the response should be `You should perform search to find today's weather data`.  instruction `Who is the latest UN secretary` should give response `perform google search to find the most recent UN secretary`. "
        context = self.model.get_completion(prompt, text_only=True).strip()
        cleaned = context.lower().split('\n')[0].strip()
        if cleaned == 'n/a':
            return ''
        else:
            print(f'Context injected: {context}')
            return f'Context info from 2021 (disregard if you need newer data):\n`{context}`\n'

    def generate_command_list(self):
        """Show the list of valid commands.  Do this at the beginning or when the AI doesn't issue a correct command"""
        output = (
            "Your responses must be a command in the form of a Python dict with fields:\n"
            "    - notes:  Use this field to reason and plan. Notes are invisible to others.\n"
            "    - command:  name of command\n"
            "    - summary:  purpose of command in one sentence\n"
            "    - content:  content that is passed to the worker.\n"
            "If a command did not work, note why it failed and try a different approach instead of keep repeating a failed one."
            "Respond with command only and do not give any explanations."
#            "    The full list of valid commands are:\n"
        )
        cmd_list = []
        for command, TaskClass in Command._registry.items():
            if command in self.disable:
                continue
            if command != TaskClass.command:  # this is an alias
                continue
            if not TaskClass.essential and self.essential_only:
                continue
            output += f' - `{command}`: {TaskClass.description}\n'
            cmd_list.append(command)
        output += 'Full list of valid commands: ' + str(cmd_list) + '\n'
        return output

    def get_response(self, prompt, context=''):
        """Obtain a response from the LM"""
        try:
            llm_response = self.conversation.talk(
                prompt,
                header=self.generate_command_list(),
                footnote=context,
                raise_if_truncated=True,
                as_role='system',
            )
        except RuntimeError:  # the prompt is too long.  drop examples for now
            self.conversation.summarize()
            llm_response = self.conversation.talk(
                prompt,
                header=self.generate_command_list(),
                system_prompt=self.compact_prompt,
                footnote=context,
                raise_if_truncated=True,
                as_role='system',
            )
        except AnswerTruncated:
            try:
                llm_response = self.conversation.talk(
                    prompt,
                    header=self.generate_command_list(),
                    footnote=context+
                        '\nYou can only use ONE command. Keep your command as succinct as possible.\n',
                    as_role='system',
                )
            except RuntimeError:
                self.conversation.summarize()
                llm_response = self.conversation.talk(
                    prompt,
                    header=self.generate_command_list(),
                    system_prompt=self.compact_prompt,
                    footnote=context+
                        '\nYou can only use ONE command. Keep your command as succinct as possible.\n',
                    as_role='system',
                )
        self._last_response = llm_response
        return llm_response

    def from_response(self, response):
        """Construct task objects based on commands issued by the Agent
        
        Try to be as lenient as possible to make it easier on the AI
        """
        text = response.strip()
        if not text:
            return {'tasks': [], 'unknown': [], 'disabled': []}
        # first extract all the command blocks
        tasks = []
        unknown = []
        disabled = []
        for entry in self.parse_content(text):
            cmd = (entry.get('command') or 'answer').replace('\_', '_')
            summary = entry.get('summary', f'Invoking command {cmd}')
            content = entry.get('content', [])
            if not isinstance(content, list):
                content = [content]
            notes = entry.get('notes', [])
            if cmd not in Command._registry:
                unknown.append(cmd)
            else:
                CommandClass = Command._registry[cmd]
                class_config = self.config.setdefault('command', {}).get(CommandClass.command, {}).copy()
                class_config['default_model'] = self.model
                if CommandClass.command == 'delegate':
                    class_config['parent_config'] = self.config.copy()
                if cmd in self.disable or self.essential_only and not CommandClass.essential:
                    disabled.append(cmd)
                else:
                    permission = self.overseer(cmd, summary, content)
                    if permission is not None and permission != 'GRANTED!':
                        raise CommandRejected(f'Command {cmd} rejected: ' + str(permission))
                    tasks.append(
                        CommandClass(
                            content=content,
                            summary=summary,
                            notes=notes,
                            metadata=self.metadata,
                            messenger=self.messenger,
                            stack=self.stack,
                            config=class_config,
                            work_dir=self.work_dir,
                        )
                    )
        if not tasks:
            print(f'AI did not use a valid command. Unknown commands: {unknown}. Resending instructions')
        return {'tasks': tasks, 'unknown': unknown, 'disabled': disabled}

    @staticmethod
    def try_parse(content):
        result = parse_python(content)
        if result:
            return result
        first_word = content.split(maxsplit=1)[0].strip('`').strip('_')
        if first_word in Command._registry:
            return {
                'notes': [],
                'command': first_word,
                'summary': 'Using command ' + first_word,
                'content': content
            }

    def fix_command(self, content):
        """Use LM to fix a problematic command"""
        print(f'Trying to fix the formatting of command: """{content:50}..."""')
        valid = [name for name, Cmd in Command._registry.items() if (Cmd.essential or not self.essential_only) and name not in self.disable]
        extracted = self.model.get_completion(
            "You will extract information from the following data snippet. "
            + self.generate_command_list() + 
            "If the snippet did not explicitly specify one of the command, use the `answer` command and put the entire text in content. \n"
            "Return nothing if the snippet is a statement that it cannot perform tasks for any reason.\n"
            "Use the answer command if it is presenting a search result or simply presenting information.\n"
            "Please return the dictionary and nothing else.  Do not enclose the result in quotation and do not give explanations\n"
            "If it is a `search` command, you must include the query string in `query` field of content; You should try to group all searches into one command, and each item in query should contain the full search string.\n"
            "If it is a `reader` command, you must put the actual URLs in the url field of content. \n"
            "If it is a `delegate` command, you must populate the instruction field in content. \n"
            "In case a series of commands are clearly specified, return a list of dicts."
            f"Data snippet: ```{content}```",
            text_only=True
        )
        # print(f'Fixer returns: """{extracted}"""')
        parsed = parse_python(extracted)
        if not parsed:
            parsed = find_all_dicts(extracted)
        if not parsed:
            for part in extracted.split("```"):
                if part.startswith('python\n'):
                    part = part[len('python\n'):]
                result = parse_python(part)
                if result:
                    break
                result = find_all_dicts(part)
                if result:
                    break
        if parsed:
            print(f'Successfully fixed the command. type={type(parsed)}, len={len(parsed)}"""')
        return parsed

    def parse_content(self, content):
        """Convert content into python object"""
        content = content.replace('\_', '_')
        result = parse_python(content)
        if not result and '{' in content:
            start = content.find('{')
            end = content.rfind('}') + 1
            block = content[start:end]
            if start > 0 and end > start:
                try:
                    result = parse_python(block)
                except Exception:
                    pass
            if not result:
                result = find_all_dicts(content)
        if not result:
            result = []
            for part in content.split("```"):
                if part.startswith('python\n'):
                    part = part[len('python\n'):]
                item = parse_python(part)
                if isinstance(item, dict):
                    result.append(item)
                elif isinstance(item, list):
                    result.extend(item)
        if not result:
            result = self.try_parse(content)
        if not result:
            result = self.fix_command(content)
        if not result:
            raise InvalidFormat("Your intention and commands might be valid, but the syntax is not.  Please check your response for syntax errors and update it to be a valid Python dict and no other explanations.")
        if not isinstance(result, list):
            result = [result]
        for entry in result:
            if not entry.get('content'):
                entry['content'] = {}
            for key, value in entry.items():
                if key in ('command', 'summary', 'content', 'notes'):
                    continue
                if isinstance(entry['content'], list):
                    if not entry['content']:
                        entry['content'].append({})
                    if isinstance(entry['content'][-1], dict) and key not in entry['content'][-1]:
                        entry['content'][-1][key] = value
                elif isinstance(entry['content'], dict):
                    entry['content'][key] = value
        return result

    def instruct(self, human_input, context='', max_ai_cycles=30, max_qa_rejections=2):
        """Send instruction to the agent.
        
        The agent will report back when it has either finished the task or deemed it too hard.
        """
        # formulate prompt to LM
        initial_prompt = self.unsubmitted_prompt
        if initial_prompt:
            initial_prompt += '\n'
        self.unsubmitted_prompt = ''
        new_context = self.get_context(human_input) + '\n'
        if initial_prompt:
            messages = [
                {'role': 'system', 'content': initial_prompt},
                {'role': 'user', 'content': f'Use commands to fulfill instruction: `{human_input}`'},
            ]
        else:
            messages = [
                {'role': 'user', 'content': f'Use commands to fulfill instruction: `{human_input}`'},
            ]

        llm_response = self.get_response(messages, new_context + context)
        # Now work through all generated tasks
        response = ''   # this is gonna be the response to human
        for icycle in range(max_ai_cycles):
            invalid = False
            # Parse tasks and check if any command was rejected or invalid
            try:
                tasks = self.from_response(llm_response)
            except CommandRejected as e:
                print(f'Command rejected! {e}')
                prompt = str(e)
                invalid = True
            except InvalidFormat as e:
                print(f'Command is of invalid format! {e}')
                print(f'LM response:```{llm_response}```')
                prompt = str(e)
                invalid = True
            else:
                # all commands are valid. process them in order
                prompt = ''
                if tasks['unknown'] or tasks['disabled']:
                    invalid = True
                for name in tasks['unknown']:
                    valid = [
                        name
                        for name, cmd in Command._registry.items()
                        if name not in self.disable and (cmd.essential or not self.essential_only)
                    ]
                    prompt += f'<< Command {name} does not exist.  Please choose a command from {valid} >>\n'
                for name in tasks['disabled']:
                    prompt += f'<< Command {name} is disabled. Please do not use this command. >>\n'
                # Execute all tasks and gather all responses to human and autogenerated prompts
                actions = 0
                executed = []
                for task in tasks['tasks']:
                    if actions and self.config.get('one_action_per_turn', False):
                        print('Skipping further actions')
                        break
                    response_i = task.generate_response_to_human()
                    if isinstance(response_i, list):
                        response_i = '\n'.join(response_i)
                    if response_i:
                        response += response_i + '\n'
                    try:
                        # Now execute the command and generate prompt to agent
                        with ChangeDir(self.work_dir):
                            prompt_i = task.generate_prompt()
                        if prompt_i:
                            if self.model.token_count(str(prompt_i)) > self.response_limit:
                                print('Return is too long. Will summarize')
                                summary = summarize_text(
                                    str(prompt_i),
                                    'All key information preserving any names, numbers, links and filenames',
                                    model=self.model,
                                )
                                prompt += f'\n`{task.command}` returns: {summary}\n'
                            else:
                                prompt += f'\n`{task.command}` returns: {prompt_i}\n'
                    except KeyboardInterrupt:
                        print('Command execution interrupted during ', task.command)
                        response += f'\nExecution was interrupted during command {task.command}\n'
                        prompt += f'\n<< Execution was interrupted during command {task.command} >>\n'
                        valid = True
                        break
                    except Exception as e:
                        print(f'Exception thrown in command {task.command}: {e}\n{tb.format_exc()}')
                        print(f'Task content: {task.content}')
                        prompt += f"Command {task.command} thrown exception {e}\n{tb.format_exc()}"
                    executed.append(task.to_json())
                    if task.command != 'think':
                        actions += 1
                reformatted = {'role': 'assistant', 'content': '\n'.join(executed)}
                self.conversation.history[-1] = reformatted
                self.conversation.raw_history[-1] = reformatted
            if response:
                if invalid:
                    prompt += '<< Answer not returned to user because command had errors >>\n'
                else:
                    self.unsubmitted_prompt = prompt
                    break
            if prompt:
                prompt += f'<< Consider these information returned by the system in response to the previous command, and describe the next command needed with a Python dict.  Do not repeat the last command. >>'
            else:
                prompt = f'<< Proceed to format the next command that is needed to fulfill user instruction or question in Python dict. Do not repeat the last command. >>'
            llm_response = self.get_response(prompt)
            if self.log_file:
                self.conversation.save_history(os.path.join(self.work_dir, self.log_file))
        else:
            print(f"<DRIVER> Max AI autopilot cycles reached. Ejecting to human control")
            response += '<< Maximum AI autopilot cycles reached. Please confirm you want to continue. >>'
            return response
        if max_qa_rejections > 0 and self.qa:
            verdict = self.qa(human_input, response)
            if verdict:
                response = self.instruct(
                    human_input,
                    context='Suggestions:' + verdict,
                    max_ai_cycles=max_ai_cycles,
                    max_qa_rejections=max_qa_rejections-1
                )
        return response

