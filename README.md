# easy_llm_agents: Easily enhance language model agents

easy_llm_agents is a versatile Python package for managing and extending language model based agents. It allows you to effortlessly teach the agent new capabilities in a few lines of code and integrate the agent into any project.

## Is this a simplified version of [langchain](https://github.com/hwchase17/langchain)?

Yes, it is a watered-down version of langchain with a little bit of added hooks for security checks and real-time integration into practical applications.  In fact it enjoys a strict subset of functionalities of that awesome package and if you are a researcher of ReAct pattern you are better off downloading langchain instead.

However, this simplification is intentional for the following reasons:

- Simplified mental model: The single concept of AI agents issuing commands reduces the learning curve and cognitive load, especially for people not familiar with the rich traditions and concepts.
- Ease of development: The package aims to make it as straightforward as possible to start building applications.

These two points are indeed true for both human and AI developers as shown by the examples below.

## Note

Although based on experimentation we believe that the risk of an AI takeover is very low for GPT-4, 
we did observe some agents installing GPT-2 and GPT-J on local systems through `huggingface`, which is disturbing to say the least.  
We therefore strongly recommend that agents not to be created on machines with direct access to GPUs or giving direct access to LLM APIs. 
If you give access to any production system, please make sure to verify its safety by properly implement an Overseer.


## How to implement a new command

You can create a command to perform a health check of your system like this:
```python
from easy_llm_agents.commands import BaseCommand

class HealthCheckCommand(
    BaseCommand,
    command='health_check',
    description="Check the health status of the frog service. The following should be supplied in content:\n    -`data`: json parameters\n\n    - `status_key`: which key to extract from api"
):
    def generate_prompt(self):
        import requests   # imports should be lazy

        resp = requests.post(f'https://mycompany.com/frog/_health?secret={self.metadata["frog_api_secret"]}', json=self.content['data'])
        if not resp.ok:
            return 'Health check failed'
        try:
            return resp.json()[self.content['status_key']]
        except:
            return 'Invalid return from health check API'
```
`command` and `description` are required arguments during class initialization.
Remember to explain fields that should be passed in content in the `description` argument.  When you define or redefine a subclass of BaseCommand, the commands will automatically update and their behavior will be modified.  

The return value of `generate_prompt()` will be given to the agent. Due to token limit, please keep the return as concise as possible.

When impementing a command, the following data will be available in a command instance:
- self.metadata:  dictionary containing info such as API keys, AWS secrets, Google application credientials, user private data etc
- self.summary:   The summary sentence passed to the command
- self.content:   The content body of the command

These correspond to the actual command that you issue like this
```python
{
   "command": "health_check",
   "summary": <summary here>,
   "content": {
     "field1": <data here>,
     "field2": <data here>
   }
}
```

## More interesting Examples

#### Teaching the Agent to Add Commands

After creating a `gpt-4` agent, we ask it to read the above section of this file, then asked it to create new commands.  It is able to create, deploy, then debug and execute the new command.
 
[![GPT-4 Agent Adds Command for Itself during Live Conversation](https://img.youtube.com/vi/s77I-LfEHaQ/0.jpg)](https://www.youtube.com/watch?v=s77I-LfEHaQ)


#### Thinking as a Separate Task

> Kate formed the distinct impression that thinking was, for
> him, a separate activity from  everything  else,  a  task  that
> needed  its  own  space.
> -- Kate's impression of *Thor* in <cite> The Long Dark Tea-time of the Soul </cite>

Thinking is a command that on paper takes no effect and indeed contains no *real* code. However, it allows the AI to reason and achieve sophisticated problem-solving skills. 
This can help the AI deal with complex problems that normally cause trouble for GPT-4. One might even view it as an extremely watered down version of [babyagi](https://github.com/yoheinakajima/babyagi).  The fact that it is a seperate command and serves no other purpose seems to be essential, as it does not perform as well if we move the instructions to system prompt and remove the command.

Here we asked a relatively convoluted question, then printed out all the logging messages to see its progress.  It planned out a long sequence of actions and adjusted for many different approaches to obtain the desired result.

[<img width="1086" alt="image" src="https://user-images.githubusercontent.com/3173151/231362669-2dfd58de-4e79-4e05-8f96-18b46a65b1e4.png">](./examples/convoluted_question.ipynb)



## Built-in Commands

The following basic commands are included by default and can be disabled as needed:

- **answer**: Basic conversation ability
- **search**: Perform searches through Google, retrieving top results and their URLs
- **read_page**: Read a page and extract specific information or a general summary using a separate `gpt-3.5-turbo` model for rolling summarizations
- **self_note**: The agent can think to itself, writing down its thoughts without taking actions or sharing its contents with users
- **python**: Write Python code and ask for any print-outs and/or the final value to be returned, with source code or files created available for the driving program to keep

## Custom Hooks for Monitoring, Control, and Interaction

Custom hooks are implemented to provide convenient ways to monitor, control, and interact with tasks created by the agent through commands.  Some example implementations 
are available in `handlers` module.

### Metadata

A metadata dictionary is attached to every conversations and made available to all task instances.  I use it to pass information such as user IDs, attributes and auth / secrets, but 
it can be used to pass any other data or objects too.  The agent does NOT have access to this data.

### Overseer

Every command issued by the Agent is first given to the Overseer before a task can be created from a command. The Overseer can reject commands and provide instructions. The default Overseer grants any requests and simply prints the command and purpose.  
**For the love of humankind please do not use the default Overseer if you have extremely powerful models or commands.**  
I would also recommend against using the same model as agent and overseer. 

### Messenger

A callback function, passed to task instances, that relays information to external driving systems in real time. Use it for logging, implementing progress bars, and other client-side chat app features.  The Python command for example, use it to notify the driving program what packages are requested to be installed, the source code executed, what variables are returned, and flag any files that are available to be downloaded.

### QA

When a response is sent to a human, QA is invoked with the original question and the agent's answer. QA can reject the answer and provide suggestions to the agent on how to improve. This is useful for ensuring high-quality responses, but keep in mind the extra time and token cost.  Two implementations are provided, one simply passes every response, the other 
use GPT to inspect the question and answer and give evaluations and suggestions accordingly.

## Disclaimer

This README is mostly generated by GPT and may have inaccuracies. Please report any issues you discover. This disclaimer is not originally written by AI.
