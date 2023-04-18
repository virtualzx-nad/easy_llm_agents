"""Execute Python code to obtain information that otherwise hard for LLMs such as numeric compute or complex logic
"""
import io
import os
import ast
import time
import traceback as tb

from .command import BaseCommand
from ..clients import get_completion, get_edit


def exec_and_return(script, globals=None, locals=None):
    '''Execute a script and return the value of the last expression
    Note this was written by GPT and looks legit in a glance.  Check more carefully when time permits
    '''
    stmts = list(ast.iter_child_nodes(ast.parse(script)))
    if not stmts:
        return None
    if isinstance(stmts[-1], ast.Expr):
        # the last one is an expression and we will try to return the results
        # so we first execute the previous statements
        if len(stmts) > 1:
            exec(compile(ast.Module(body=stmts[:-1], type_ignores=[]), filename="<ast>", mode="exec"), globals, locals)
        # then we eval the last one
        return eval(compile(ast.Expression(body=stmts[-1].value), filename="<ast>", mode="eval"), globals, locals)
    else:
        # otherwise we just execute the entire code
        return exec(script, globals, locals)


class PythonCommand(BaseCommand,
    command='python',
    description="""Submit Python code that perform complex tasks or computations. Printouts or error messages will be returned to you. If you do not explicitly create a file it will not be created. The content must be a Python dictionary with fields:
    - code: Required field.  A string containing the code snippet
    - request_file: Optional. Request files to be supplied; 
    - save_as:  Optional. String. Filename for the code to be saved as; do not include path.
    - return_variables:  Optional. List of variable names that you need to be returned after the code is executed
    - packages: Optional. A list of packages that need to be installed
    - execute: Optional.  If False, the code will be saved but not executed. Default is True.
    - note: any important messages. If you are unable to directly execute, put a message in `note`, code that you cannot execute in the `code` field, and do not return an `execute` field.
"""
):
    edit_instructions = [
        'Fix the error in the provided Python snippet',
        'The provided Python snippet throws exception {exception}. Please fix it',
        'The provided Python snippet throws exception {exception}. Please fix it and pay special attention to escaping characters in strings.',       
    ]

    def generate_prompt(self):
        """Take the python code it write and run them"""        
        stdout_buffer = io.StringIO()
        if isinstance(self.content, list):  # Need future work to handle multiple scripts in one command
            if len(self.content) > 1:
                self.send_message(info='More than one script passed in Python but only one can be executed for now')
            run_spec = self.content[0]
        else:
            run_spec = self.content
        for pkg in run_spec.get('packages', []):
            self.send_message(action='install_package', package=pkg)
        if run_spec.get('note'):
            self.send_message(info=run_spec['note'])
        # Load any variables saved in previous sessions that are requested
        loc = {"print": lambda x: stdout_buffer.write(f"{x}\n")}
        saved_vars = self.metadata.get('stored_variables', {})
        for key, value in saved_vars.items():
            loc[key] = value
        # Extract code string
        code_string = run_spec.get('code')
        if not code_string:
            return 'Source code not found.  Make sure to provide source code even if you believe you cannot execute it'
        self.send_message(info="Executing code snippet", code=code_string)
        save_vars = run_spec.get('return_variables', [])
        if isinstance(save_vars, str):
            save_vars = [save_vars]
        result = {'variables': {}}
        curr_dir = os.getcwd()
        start_time = time.time()
        if run_spec.get('execute', True):
            try:
                result['last_expression_value'] = exec_and_return(code_string, {}, loc)
            except Exception as e:  # ok it errors out.  No biggie.  Try all kinds of stuff to make it work
                # first try to fix the snippet twice with edit model then gpt 4
                for instruction in self.edit_instructions:
                    try:
                        edited = get_edit(code_string, instruction, model='code-davinci-edit-001', text_only=True)
                        result['last_expression_value'] = exec_and_return(edited, {}, loc)
                    except Exception:
                        continue
                    else:  # use gpt-4 to correct as last ditch effort
                        edited = get_completion(
                            "A syntax error is reported in the following code snippet. "
                            "Please correct the syntax error and make no other changes.  "
                            "Return the executable code only with no markups. "
                            "Please refrain from making any explanations. "
                            "If you absolutely have to  please put them as comments.\n```"
                            + code_string + "```\n", model='gpt-4', text_only=True).strip('```')
                        try:
                            result['last_expression_value'] = exec_and_return(edited, {}, loc)
                        except Exception as e2:   # really can't fix this sorry
                            self.send_message(info=' AI authored Python script errored out', exception=e2, traceback=tb.format_exc())
                            result['error'] = str(e2)
                            result['traceback'] = tb.format_exc()
                            result['instruction'] = 'Python script errored out.  Please check and fix syntax and logic errors.'
        for variable in save_vars:
            self.metadata.setdefault('stored_variables', {})[variable] = loc.get(variable)
            result['variables'][variable] = loc.get(variable)
        result['printout'] = stdout_buffer.getvalue()
        if run_spec.get('save_as'):
            self.send_message(info=f'Saving source code to {run_spec["save_as"]}')
            with open(run_spec["save_as"], 'w+') as f:
                f.write(code_string)
        for fname in os.listdir(curr_dir):
            fullname = os.path.join(curr_dir, fname)
            if os.path.getmtime(fullname) > start_time:
                self.send_message(
                    info=f'File created or modified after execution',
                    action='output_file',
                    filename=fullname,
                )
        return result