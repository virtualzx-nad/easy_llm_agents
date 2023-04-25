# Note
The structure here does not work well on llamas.  Redesigning it and will create a different repo and migrate over later.  


# easy_llm_agents: Easily enhance language model agents

easy_llm_agents is a versatile Python package for managing and extending language model based agents. It allows you to effortlessly teach the agent new capabilities in a few lines of code and integrate the agent into any project.

## Is this a simplified version of [langchain](https://github.com/hwchase17/langchain)?

Yes, it is a watered-down version of langchain with a little bit of added hooks for security checks and real-time integration into practical applications.  In fact it enjoys a strict subset of functionalities of that awesome package and if you are a researcher of ReAct pattern you are better off downloading langchain instead.

However, this simplification is intentional for the following reasons:

- Simplified mental model: The single concept of AI agents issuing commands reduces the learning curve and cognitive load, especially for people not familiar with the rich traditions and concepts.
- Ease of development: The package aims to make it as straightforward as possible to start building applications.

These two points are indeed true for both human and AI developers as shown by the examples below.  You can see that we do not even have to specify an agent style, because reasoning is coded as an act, and it is fully left to the agent to decide how it operates.

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

        resp = requests.post(f'https://mycompany.com/frog/_health?secret={self.metadata["frog_api_secret"]}', json=self.content[0]['data'])
        if not resp.ok:
            return 'Health check failed'
        try:
            return resp.json()[self.content[0]['status_key']]
        except:
            return 'Invalid return from health check API'
```
`command` and `description` are required arguments during class initialization.
Remember to explain fields that should be passed in content in the `description` argument.  When you define or redefine a subclass of BaseCommand, the commands will automatically update and their behavior will be modified.  

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

## More interesting Examples

#### Teaching the Agent to Add Commands

After creating a `gpt-4` agent, we ask it to read the above section of this file, then asked it to create new commands.  It is able to create, deploy, then debug and execute the new command.  We will leave details to images below because the test case actuall search for and read this very document, so we do not want to give too much away here:

[<img width="1131" alt="image" src="https://user-images.githubusercontent.com/3173151/231618330-b7555f18-799b-446a-b3de-dd49516b4d5e.png">](./examples/learn_a_new_trick.ipynb)

Then it show me what to do
<img width="632" alt="image" src="https://user-images.githubusercontent.com/3173151/231618716-036d5a49-ed5d-4896-93d2-8045d3829ce9.png">

which I would complied, but for obvious reasons that is not screenshotted here.  It is then asked to actually perform a task to test this out, and here is where it gets interesting.  Bug was found, fixed, but actually not fixed, then fixed again, when it finally worked.  

<img width="1094" alt="image" src="https://user-images.githubusercontent.com/3173151/231619102-cdbca787-51b6-417d-b7b9-f05823c85ef6.png">
and finally gave the desired results.
<img width="1097" alt="image" src="https://user-images.githubusercontent.com/3173151/231619178-a829c569-b1af-4a16-934b-c03092bd1a3e.png">
The command is also saved so that it can now be used in future sessions as well!  


#### Thinking as a Separate Task

> Kate formed the distinct impression that thinking was, for
> him, a separate activity from  everything  else,  a  task  that
> needed  its  own  space.
> -- Kate's impression of *Thor* in <cite> The Long Dark Tea-time of the Soul </cite>

Thinking is a command that on paper takes no effect and indeed contains no *real* code. However, it allows the AI to reason and achieve sophisticated problem-solving skills.  To compare this with Chain-of-Though vs ReAct style of reasoning, there is basically no differentiation of `act` and `thought` from 
the agent's point of view.  It can freely choose to perform CoT or ReAct or act-only at any point.  What we observe is that it generally choose to do a CoT when significantly new information is obtained, and does ReAct in other situations.

This can help the AI deal with complex problems that normally cause trouble for GPT-4. Through the note command the agent keeps a dynamic task list that it revises over time, removing the need to engineer a task management system.  One might even view it as an extremely watered down version of [babyagi](https://github.com/yoheinakajima/babyagi).  The fact that it is a seperate command and serves no other purpose seems to be essential, as it does not perform as well if we move the instructions to system prompt and remove the command.

Here we asked a relatively convoluted question, then printed out all the logging messages to see its progress.  It planned out a long sequence of actions and adjusted for many different approaches to obtain the desired result.

[<img width="1086" alt="image" src="https://user-images.githubusercontent.com/3173151/231362669-2dfd58de-4e79-4e05-8f96-18b46a65b1e4.png">](./examples/convoluted_question.ipynb)

### Composing full length novel

Here we demonstrate how an agent can plan fairly complex activities to write a book.  Now we all know GPT can write books and most of us probably have tried or read a few works from it already.  However, it's compositions, while coherent in a short volume, tend to drift and lose focus in the long run, suffer from a lack of focus.  It is also limited by the token limit.

Here we show an example where we assign a very complex and detailed task to the agent.  It is able to plan and execute the action and write a novel
[<img width="1204" alt="image" src="https://user-images.githubusercontent.com/3173151/233288356-46a4b9bb-6f12-40c5-901c-015c2b61cb11.png">](./examples/write_a_scifi_novel.ipynb)

Note that we gave a fairly large number of requirements, but did not explain how to do them.  We also do not prescribe how the agent should think or act 
other than prompt, and we do not provide any mechanism to track task lists externally.  It will do so with it's own verbal reasoning.  A single request 
is given, and we do not review or modify any plan, or give any feedback.  The book was finished without input, in ~1.5 hours (disappointingly slow thanks to GPT-4).

Here are the steps that we observe the agent has taken
- It performed google searches to find recent scientific discoveries and read those websites to get a list of scientific [discoveries](./examples/scifi/discoveries.txt). The following news articles are incorporated into the technologies of the imaginary world.  Here I list them to ensure credits given when they are due:
     1. [T (iNKT) Cells home in on skin to provide immunity for infants](https://scitechdaily.com/scientists-discover-new-property-of-immune-cells-like-guided-missiles/)
     1. [High altitude changes your metabolism](https://scitechdaily.com/new-research-reveals-how-high-altitude-changes-your-bodys-metabolism/)
     2. [Nano bacterial machines for medication](https://scitechdaily.com/natures-nano-syringes-harnessing-bacterial-machines-for-next-gen-medicine/)
     3. [30,000 unknown viruses found hiding in microbial DNA](https://www.sciencedaily.com/releases/2023/04/230411105915.htm)
     4. [Embryo-like structure created from monkey stem cells](https://www.sciencedaily.com/releases/2023/04/230406113953.htm)
     5. [Light-activated graphene "tattoo" used in cardiac implants](https://www.technologynetworks.com/diagnostics/news/cardiac-arrhythmia-treated-by-graphene-tattoo-using-light-372275)
     6. [Wearable bio-censors](https://www.technologynetworks.com/applied-sciences/news/wearable-biosensor-detects-minute-biological-signals-372209)
     7. [New metric to count human ecological footprints](https://www.sciencedaily.com/releases/2023/04/230418011126.htm)
     8. [Molecular motors](https://scitechdaily.com/driving-genetic-discovery-new-insights-into-dna-replications-molecular-motor/)
- The topic is chosen to be Celestial Ark, literally a 50/50 mix of Carl Sagan (celestial) and Yuval Noah Harari(ark).  The technologies gathered above are used for world building [world building](./examples/scifi/world_building.md).
- It then developed a set of [characters](./examples/scifi/characters.md) based on the world setting.
- A [story arc](./examples/scifi/story_arcs.md) was then developed, assigning an overall story for each book and a plot twist. Curiously, it did not develop plot lines to the chapter level; this causes quality issues later.  
- Drafts for each book chapter was written
- Drafts are modified and final chapters are stored. The book as a total of 14500 tokens, which is fairly short. Here is a list of final chapter versions
    - Book I. The Genesis of the Celestial Ark
      - Chapter 1 [A New Beginning](./examples/scifi/book1_chapter1.md) 1166 Tokens
      - Chapter 2 [Seeds of Resistance](./examples/scifi/book1_chapter2.md) 925 Tokens
      - Chapter 3 [The Art of the Stars](./examples/scifi/book1_chapter3.md) 901 Tokens
    - Book II. Secrets of the Cosmos
      - Chapter 1 [The Enigma of the Stars](./examples/scifi/book2_chapter1.md) 1066 Tokens
      - Chapter 2 [Whispers of the Ancients](./examples/scifi/book2_chapter2.md) 1091 Tokens
      - Chapter 3 [The Dark Matter Conundrum](./examples/scifi/book2_chapter3.md) 980 Tokens
    - Book III. Shadows of the Past
      - Chapter 1 [Whispers of Intrigue](./examples/scifi/book3_chapter1.md) 1000 Tokens
      - Chapter 2 [Bonds and Betrayal](./examples/scifi/book3_chapter2.md) 974 Tokens
      - Chapter 3 [Unraveling the Hidden](./examples/scifi/book3_chapter3.md) 895 Tokens
    - Book IV. The Gardeners of Worlds
      - Chapter 1 [A New Horizon](./examples/scifi/book4_chapter1.md) 914 Tokens
      - Chapter 2 [The Awakening](./examples/scifi/book4_chapter2.md) 903 Tokens
      - Chapter 3 [Unseen Perils](./examples/scifi/book4_chapter3.md) 1028 Tokens
    - Book V. The Reckoning
      - Chapter 1 [A Tenuous Alliance](./examples/scifi/book5_chapter1.md) 904 Tokens
      - Chapter 2 [Unlikely Allies](./examples/scifi/book5_chapter2.md) 1056 Tokens
      - Chapter 3 [A Tenuous Alliance](./examples/scifi/book5_chapter3.md) 1104 Tokens

Here is a GPT summary of the entire book:
```The Celestial Ark is a massive interstellar vessel designed to transport a diverse population of humans and other Earth species to a habitable exoplanet in the distant star system of Alpha Centauri. A group of disgruntled citizens formed a resistance movement called "Earth's Reclaimers," which plots to sabotage the Ark's launch. The crew discovers an uncharted star system with a planet that contains ancient alien artifacts. They unwittingly awaken an ancient and powerful force that could pose a threat to their mission. The crew races against time to contain the destructive force of an unstable dark matter entity. As they draw closer to their destination, they would be forced to confront the true nature of their enemy – and the depths to which they were willing to go to ensure humanity's future. The tension aboard the Celestial Ark grew as they neared their destination. Every member of the crew knew that adapting to life on Eden would not be easy. However, unbeknownst to them, a hidden danger lurked within the depths of Eden's oceans - a danger that could threaten not only their new home but also their very existence. The crew must form an alliance with Earth's Reclaimers to confront the looming threat of the parasitic entity ominously dubbed 'The Devourer.' They work tirelessly to decipher the ancient alien messages hidden within the artifacts and uncover a possible solution to defeat The Devourer. The key lay in harnessing the power of a mysterious energy source, one that had been hidden away by the ancient civilization that once ruled the cosmos. They discovered that this living energy, dubbed 'The Essence,' possessed the power to destroy The Devourer, but it required a host – a human capable of channeling its immense power. As they pondered who amongst them would be suitable for such a monumental task, an urgent message arrived from their scouts monitoring The Devourer. It had begun to awaken, sensing the presence of life on their new world. The countdown to destruction had begun. With each passing moment, the alliance grew stronger and more determined. As they prepared for the final confrontation with The Devourer, these former enemies would stand together as one, bound by a common goal: survival.```

Analysis: 
What it did well
 - The agent was able to plan the action and satisfy almost all the requirement in one single prompt with no feedback
 - Characters are fairly well developed and world setting is rich
 - The work is above token limit for GPT but generally consistent throughout
 - There are some plot twists around
 - Very new scientific findings were incorporated into them, many were in the news *today*
 
What it did not do well
 - It created 3 chapters per book instead of 10. By now it is well-known that GPT does not count.
 - Each chapter is rather short and details are lacking.  Literary style is quite mediocre overall.
 - It did not initially develop the plot-lines to chapter level.  As a result, Book 5 chapters have some overlaps
 - Chapter to chapter transition is generally not very good.  It could have read adjacent chapters but did not.
 - Scientific concepts are added in in a fairly intrusive manner.
 - It took a very long time.
 
Overall conclusion:  

It did honor almost all of the requirements.  The overall quality of the book is perhaps suited more for a computer game 
than an literary work.  

The agent is curiously literal when it comes to fulfilling the command, which certainly lead us to think about the alignment problem. 
When we asked it to mix to authors it does that literally by taking a theme from each author and mixing them half and half.  Note that we did other runs and it sometimes assigned exactly half the chapters to follow Sagan and half to follow Harari's styles. This fulfills what we said, but is clearly not what we meant.
When we asked it to end books with cliffhangers, it literally created a cliffhanger for each book in the outline, even the last book.  As a result there is no proper ending.  Again the motives of our requirement were not understood.
When we asked it to incorporate recent findings it literally looked up a set of them and pretty much put one concept into each chapter.
Overall I think it did a surprisingly good job organizing a fairly complex process, and the book is decent.


## Built-in Commands

The following basic commands are included by default and can be disabled as needed:

- **answer**: Basic conversation ability
- **search**: Perform searches through Google, retrieving top results and their URLs
- **reader**: Read a page and extract specific information or a general summary using a separate `gpt-3.5-turbo` model for rolling summarizations
- **writer**: Write a file, either code or text.  We use a sliding window approach to progressively compose the file so that target files much larger than context window can be composed.
- **self_note**: The agent can think to itself, writing down its thoughts without taking actions or sharing its contents with users
- **python**: Write Python code and ask for any print-outs and/or the final value to be returned, with source code or files created available for the driving program to keep
- **delegate**: Delegate a group of isolated tasks to another agent then collect the results.

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
