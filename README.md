# easy_llm_agent


# Basic philosophy
The basic goal is to make this package as easy to extend as a programmer as possible. 
To this end, 

1. Easy to extend.

We make extensive use of subclasses so that you should be able to easily add command or models
without having to change the code base. 

Simply subclass a command or model and any agents will immediately have access.  

In fact, you can create new command in the middle of a ongoing process if you wish, and the agent can 
also create command for itself on the fly and start using it immediately, in the same live Python session.

3. Maximum tolerance

We make the opposite assumption with many similar projects and declare our estimation that Language Models are 
dumb, and will stay dumb for the foreseeable future.  As such, the utmost amount of effort will go into making 
all tasks as easy as possible for the models.  

This usually means extensively breaking any single task to many sub-tasks if possible.   
We will also try to salvage whatever broken mistake of a command the LM issues.  If LM tends to make a mistake 
on a command syntax for example, we will make sure we can read that incorrect input instead of adjusting prompt 
to make it do the right thing.

4. Trust and verify.  

We strive to give the LM autonomy on a wide range of tasks such as choosing between engaging 
chains of thought, planning or action, setting the relevant context of actions, picking relevant files etc.  We do not 
prescribe goals, agent-behavior patterns, etc.  At the same time, we always make the assumptions they will constantly 
make wrong choices and will use second opinions and cold logic to supplement their input.  



## How to implement a new command

You can create a command to perform a health check of your system like this:
```python
import requests
from lm_agents.commands import Command

class HealthCheckCommand(
    Command,
    command='health_check',
    description="Check the health status of the frog service. The following should be supplied in content:\n    -`data`: json parameters\n\n    - `status_key`: which key to extract from api"
):
    def generate_prompt(self):

        resp = requests.post(f'https://mycompany.com/frog/_health?secret={self.metadata["frog_api_secret"]}', json=self.content[0]['data'])
        if not resp.ok:
            return 'Health check failed'
        try:
            return resp.json()[self.content[0]['status_key']]
        except:
            return 'Invalid return from health check API'
```
`command` and `description` are required arguments during class initialization.
Remember to explain fields that should be passed in content in the `description` argument.  When you define or redefine a subclass of Command, the commands will automatically update and their behavior will be modified.  

The return value of `generate_prompt()` will be given to the agent. Due to token limit, please keep the return as concise as possible.

When impementing a command, the following data will be available in a command instance:
- self.metadata:  dictionary containing info such as API keys, AWS secrets, Google application credientials, user private data etc
- self.summary:   The summary sentence passed to the command
- self.content:   The content body of the command. Usually a list of dicts, in case a command has multiple actions.  In case you are only doing one thing, just use the first element.

These correspond to the actual command that you issue like this
```python
{
   "command": "health_check",
   "summary": <summary here>,
   "content": [
     {"field1": <data here>, "field2": <data here>},
     ...
   ]
}
```


