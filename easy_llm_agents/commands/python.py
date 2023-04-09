"""Execute Python code to obtain information that otherwise hard for LLMs such as numeric compute or complex logic
"""
import io
import os
import ast
import sys
import uuid
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
    command='PYTHON',
    description='Execute Python command to perform complex tasks or computations.',
    additional_context=(
        "You can gain information and perform complex tasks by executing Python scripts using the PYTHON command.  "
        "Printouts will be given to you, if the script executed successfully, and the error info otherwise. "
        "If you would like to create a file for the user, create it in the current folder and it will be delivered. "
        "If you would like to keep the source code in a file, add the following line into your response: `KEEP_FILE filename_to_be_saved.py`; otherwise the user will not see the source code. "
        "If you do not intend the code to be executed and only want to save the source code, please include this line `NO_EXECUTION`.  "
        "If you need the value of an variable, add the line into your response: `RETURN_VARIABLE variable_name`.  "
        "DO NOT refer to the path of the generated file in any following conversations as it will be moved."
    )
):
    def generate_prompt(self):
        """Take the python code it write and run them"""
        run_id = str(uuid.uuid4())
        stdout_buffer = io.StringIO()
        save_vars = []
        execution = True
        for line in self.content.split('\n'):
            if line.startswith('KEEP_FILE '):
                keep_file = line[len('KEEP_FILE '):].strip()
                self.send_message(info='Agent requested source code to be exported')
            if line.startswith('RETURN_VARIABLE '):
                save_vars.append(line[len('RETURN_VARIABLE '):].strip())
            if line.strip() == 'NO_EXECUTION':
                self.send_message(info='Code will not be executed per request')
                execution = False
        else:
            keep_file = None
        code_string = self.content
        if '```' in code_string:
            parts = code_string.split('```')
            if len(parts) > 1:
                code_string = parts[1]
            else:
                code_string = parts[0]
            if code_string.startswith('python\n'):   # it is using markdown with language specified
                code_string = code_string[len('python\n'):]
        lines = code_string.split('\n')
        keep = []
        for line in lines:
            if line.startswith('!pip install '):
                pkg = line[len('!pip install '):].strip()
                self.send_message(info=f'AI requested installation of {pkg}.', package=pkg)
            elif not line.startswith('KEEP_FILE ') and not line.startswith('RETURN_VARIABLE ') and not line.strip() == 'NO_EXECUTION':
                keep.append(line)
        code_string = '\n'.join(keep)
        self.send_message(info="Executing code snippet", code=code_string)
        with tempfile.TemporaryDirectory() as tmpdir:
            with ChangeDir(tmpdir):
                try:
                    if execution:
                        loc = {"print": lambda x: stdout_buffer.write(f"{x}\n")}
                        output = exec_and_return(code_string, {}, loc)
                        # print('<PYTHON>Snippet output is ', output)
                        if output is not None:
                            stdout_buffer.write(f'{output}\n')
                        if save_vars:
                            stdout_buffer.write('Returned variables:}')
                        for variable in save_vars:
                            stdout_buffer.write(f'  {variable}={loc.get(variable)}')
                        output = stdout_buffer.getvalue()
                        if output:
                            return "INFO\n" + output
                        else:
                            return 'Python finished with no output.  If you need the output make sure you print the value out or return it.'
                    return 'Python script was not executed per request'
                except Exception as e:
                    self.send_message(info=' AI authored Python script errored out', exception=e, traceback=tb.format_exc())
                    return f"""Python excution thrown an error: {str(e)}
{tb.format_exc()}
Please rewrite your script. Please be creative and try different methodologies.
"""
                finally:
                    if keep_file:
                        self.send_message(info=f'Saving source code to file {keep_file}')
                        with open(keep_file, 'w+') as f:
                            f.write(code_string)
                    for fname in os.listdir(tmpdir):
                        self.send_message(
                            info=f'Output file available (they will be deleted if you do not retrieve now)',
                            filename=os.path.join(tmpdir, fname)
                        )
