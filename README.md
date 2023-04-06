# llm_agents: Enhance LLMs with Extensions and Integrate Them into Your Project

llm_agents is a flexible Python package for managing and extending Language Model (LLM) based agents. You can easily teach the agent new abilities in just a few lines of code and immediately invoke the agent anywhere.

## Features

- Teach your agent new abilities with minimal code
- Invoke the agent in any context
- Comes with built-in functionalities such as talking, Google search, page reading, and thinking

## Example: Adding Health Check Task

Teach an agent to perform a health check of your system like this:

```python
import requests
from llm_agents.base_task import BaseTask

class HealthCheckTask(BaseTask, command='HEALTH_CHECK', description='Check the health status of the frog service'):
    def generate_prompt(self):
        resp = requests.get('https://mycompany.com/frog/_health')
        if not resp.ok:
            return 'Health check failed'
        try:
            return resp.json()['status']
        except:
            return 'Invalid return from health check API'
```

Then you can directly interact with the agent:

```
<user> hmm, it will need to write a strongly worded email to jim if our frog service still down.  is it anyways?
<agent> Unfortunately the frog service has a health check status of `red` indicating it is down.  Do you want me to help you write the email?
```

## Built-in Functionalities

- **Talking**: Basic conversation ability
- **Google search**: Perform one or more searches through Google and retrieve top results and their URLs without needing API keys
- **Page reading**: Read a page and extract specific information or a general summary using a separate `gpt-3.5-turbo` model for rolling summarizations
- **Think**: The agent can think to itself and write down its thoughts without taking actions or sharing its contents with users, which is crucial for making correct decisions

## Background

This package was initially created to address the issue of lacking real-time data and facts with GPT and to experiment with ways to incorporate data services into LLMs.

When OpenAI announced Plug-Ins, migration to a plugin was considered due to the strong similarities between the implementations. However, the long waitlist, lack of implementation details, and lack of flexibility led to the continuation of this project.

We believe that many others also need:

- The ability to extend language model capabilities without being confined by vendor restrictions
- Integration of AI agents, smart workers, and chatbots with enhanced functionalities into their own infrastructure and products
- More direct control over system setup and model configurations
- A system that can be migrated to open, cheaper, or more accessible models


## Disclaimer

This README is generated by GPT and may have inaccuracies that we did not notice.  Please report any issues you have discovered.
