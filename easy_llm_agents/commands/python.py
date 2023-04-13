"""Execute Python code to obtain information that otherwise hard for LLMs such as numeric compute or complex logic
"""
import io
import os
import ast
import sys
import uuid
import json
import time
import tempfile
import traceback as tb

from .command import BaseCommand

class ChangeDir:
    """A context manager for changing the current directory while also preserving the current path in search path
    Note this was written by GPT and looks legit in a glance.  Check more carefully when time permits.
    """
    def __init__(self, path):
        self.path = path
        self.current_dir = os.getcwd()
        self.current_dir_in_sys_path = self.current_dir in sys.path
    
    def __enter__(self):
        os.chdir(self.path)
        if not self.current_dir_in_sys_path:
            sys.path.append(self.current_dir)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.current_dir)
        if not self.current_dir_in_sys_path:
            sys.path.remove(self.current_dir)


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
    description="""Submit Python code that perform complex tasks or computations. Printouts or error messages will be returned to you. The content must be a Python dictionary with fields:
    - code: Required field.  A string containing the code snippet
    - request_file: Optional. Request files to be supplied; 
    - save_as:  Optional. String. Filename for the code to be saved as; do not include path.
    - return_variables:  Optional. List of variable names that you need to be returned after the code is executed
    - packages: Optional. A list of packages that need to be installed
    - execute: Optional.  If False, the code will be saved but not executed. Default is True.
    - note: any important messages. If you are unable to directly execute, put a message in `note`, code that you cannot execute in the `code` field, and do not return an `execute` field.
"""
):
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
        code_string = run_spec.get('code')
        if not code_string:
            return 'Source code not found.  Make sure to provide source code even if you believe you cannot execute it'
        self.send_message(info="Executing code snippet", code=code_string)
        save_vars = run_spec.get('return_variables', [])
        if isinstance(save_vars, str):
            save_vars = [save_vars]
        result = {'variables': {}}
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = self.metadata.get('work_dir', tmpdir)
            with ChangeDir(work_dir):
                start_time = time.time()
                try:
                    if run_spec.get('execute', True):
                        loc = {"print": lambda x: stdout_buffer.write(f"{x}\n")}
                        result['last_expression_value'] = exec_and_return(code_string, {}, loc)
                        for variable in save_vars:
                            result['variables'][variable] = loc.get(variable)
                        result['printout'] = stdout_buffer.getvalue()
                except Exception as e:
                    self.send_message(info=' AI authored Python script errored out', exception=e, traceback=tb.format_exc())
                    result['error'] = str(e)
                    result['traceback'] = tb.format_exc()
                    result['instruction'] = 'Python script errored out.  Please check and fix syntax and logic errors.'
                finally:
                    if run_spec.get('save_as'):
                        self.send_message(info=f'Saving source code to {run_spec["save_as"]}')
                        with open(run_spec["save_as"], 'w+') as f:
                            f.write(code_string)
                    for fname in os.listdir(work_dir):
                        fullname = os.path.join(work_dir, fname)
                        if os.path.getmtime(fullname) > start_time:
                            self.send_message(
                                info=f'File created or modified after execution',
                                action='output_file',
                                filename=fullname,
                            )
        return result