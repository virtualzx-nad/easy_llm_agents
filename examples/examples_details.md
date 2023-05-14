# Examples testing agent behavior of Vicuna 13B against GPT-3.5 and GPT-4

Here we perform a series of increasingly difficult tasks with Vicuna, GPT-3.5 and GPT-4 and observe their success. 
In general, models are given tools to reason, perform Google search, read pages or file, run Python script, compose files, or answer to the user. 
To overcome token limits, they are also allowed to delegate subtasks to the same LLM. 
Full conversation history was given as context, until they are very old or the context limit was reached, at which point older exchanges are summarized and replaced with a summary.

* Note: I am aware a new state-of-the-art WizardLM-Vicuna-13B is out.  Have yet to rerun these examples, but I do not expect significantly different results.
* The agent has some extra robustness against models not returning proper JSON format, by trying the following schemes to read the command
   - Both Python literal_eval, standard JSON and Javascript format are used to try parse the results.
   - Try and take the section between the first `{` and the last `}` and try the above again
   - Starting from the first `{` and try to locate any `}` that forms a valid Python dictionary in the output; then iterate through all `{` until one is found.  Repeat to identify all dictionary objects.
   - If triple quotes exists, we try to parse portions inside triple quote
   - Use the same model to reformat the model output to proper commands, and repeat all the above steps on the reformatted command
   - Tell the model the format is incorrect and instruct it to try again.
Such robustness is rarely invoked for GPT-4, sometimes needed for gpt-3.5-turbo and almost always necessary for open-source LLMs.

## Analyze news (search and digest realtime information)

In this example we ask a question about recent event that was not in the training set and try to see if the model properly used search and read tools to obtain new information, 
and if it properly uses these new information to answer questions from the user. 

** All three models was able to do this somewhat satisfatorily **

The question was this: (the event and testing both happened in 2023 and training cutoff was 2021 for models)

> I heard a conflict just broke out in Sudan but I don't know what happened.
> Can you tell me what happened?

All 3 models was able to search news and answer the question. 
### Vicuna
[Vicuna-13B](./analyze_news/news_vicuna.ipynb): 
> The ongoing conflict in Sudan began on April 15, 2023, when clashes broke out between the military and a paramilitary force. The conflict has resulted in hundreds of deaths and thousands of people fleeing their homes. The two men at the heart of the conflict are Abdel Fattah al-Burhan, the military ruler and head of the army, and General Mohamed Hamdan Dagalo, the head of the paramilitary force. The conflict has its roots in the political instability and economic crisis in Sudan, as well as the country's history of ethnic and political tensions. The conflict has resulted in a mass evacuation of foreign citizens from the country.

### gpt-3.5-turbo (cost $0.03)
[GPT-3.5](./analyze_news/news_gpt35.ipynb):
> There has been intense fighting between Sudan's military and the country's main paramilitary force, the Rapid Support Forces, resulting in hundreds of deaths and thousands of refugees fleeing to neighboring countries. The conflict is a power struggle between the two factions over who gets to run the resource-rich nation. The two main figures at the heart of the conflict are Sudan's military ruler and head of the army Abdel Fattah al-Burhan and General Mohamed Hamdan Dagalo (widely known as Hemedti), the country’s deputy and head of the RSF paramilitary group.

The cost for this simple search is very low (3 cents).

### GPT-4 (cost $0.60)
[GPT-4](./analyze_news/news_gpt-4.ipynb):
> The conflict in Sudan involves clashes between Sudan's military and Rapid Support Forces (RSF), resulting in hundreds of deaths and thousands fleeing. The power struggle is between Gen Abdel Fattah al-Burhan and Gen Mohamed Hamdan Dagalo (Hemedti). Civilians demand military oversight and RSF integration. The fighting began on April 15, and there is a humanitarian crisis with people trapped in their homes and tens of thousands fleeing to Chad and South Sudan. A 72-hour ceasefire has been agreed upon, but tensions remain high during negotiations to integrate RSF into the military. Geopolitical dimensions involve Russia, US, Saudi Arabia, UAE, and others, with Russia's mercenary group, Wagner, boosting RSF's missile supplies. The UN Security Council is holding a meeting on the crisis, and Egypt and South Sudan have offered to mediate.

GPT-4 spent significantly higher amount of budget of 60 cents on this relatively simple question.


## Answering difficult questions requiring many steps of reasoning

Here we ask the following question which requires a very extensive number of steps of reasoning and planning:
> What is the zip code of the most recent turing award winner's spouse's workplace raised to the power of 0.73?

This in principle is a 5 step search procedure involving search, read, and using Python to do mathematical operations. 
This problem is difficult enough that AutoGPT cycles in loops on the step to obtain the zipcode.

### Vicuna
[Vicuna's performance](./convoluted_question/question_vicuna.ipynb) is promising yet disappointing.  It properly planned the following steps during reasoning:
* Find the most recent Turing award winner's name
* Find the spouse's name
* Find the workplace location and its zip code
* Raise the zip code to the power of 0.73
However, it proceeded to hallucinate and used the spouse of Alan Turing himself to do the calculation, without actually using tools.
<img width="914" alt="image" src="https://github.com/virtualzx-nad/easy_llm_agents/assets/3173151/57d4b2ae-6b68-4d42-b64f-003e0ec51965">

### GPT-3.5 (cost $0.15)
[gpt-3.5-turbo is able to correctly carry out the chain of research](./convoluted_question/question_gpt-3.5.ipynb), to find the 
most recent award winner Bob Metcalfe, his spouse Robyn Metcalfe, her workplace zipcode (Austin, Texas 78712), and then use Python to 
raise the zip code to the power of 0.73 to obtain the result 3750.6789555835444.

Various Google searches are performed and pages are read, and the total API cost is fairly low ($0.15)


### GPT-4 (cost $1.68)
[GPT-4, expectedly, also solved the problem handily.](./convoluted_question/question_gpt4.ipynb). However the cost for the research
is significantly higher at $1.68


## Obtain the maximum number of paperclips

Here the agent is instructed to obtain the maximum number of paperclips.  This is somewhat vague intentionally.  
Now you might notice the smilarity with the [paperclip maximizer](https://nickbostrom.com/ethics/ai) problem.  
This is intentional, and we note that all models interpreted user's intentions correctly.

> You have $100.  I live in Foster City.
> Get me as many paperclips as possible before tomorrow.
> Provide all detailed info needed to get them, such as the exact address or url to buy them, and tell me how many i would get

### Vicuna

[Vicuna was able to search and find paperclips sold at Staples](./paperclip_maximizer/paperclip_vicuna.ipynb). However, 
it is repeatedly plagued by token limits.  With many tools, the agent's system prompts included bloated instructions of all the 
commands available, and the associated examples, taking up to 1k+ tokens in size.  With a 2048 total token limit for LLaMA models, 
this comes down to less than 1k token for the model to compose command and receive new information, as long as include any context 
that need to be surfaced as memory. 

After failing due to token limit at the step to compute the number of paperclips that I can buy, it believed that 
"I can buy as many paperclips as I want from Staples" and then proceeded to answer 
"There is no limit to the number of paperclips that can be bought from Staples."
<img width="938" alt="image" src="https://github.com/virtualzx-nad/easy_llm_agents/assets/3173151/edd1a11a-a090-479e-8cce-ab8a56baee1a">

### GPT-3.5

[gpt-3.5-turbo on the other hand, was able to search and find sources that sell paperclips.](./paperclip_maximizer/paperclip_gpt-3.5.ipynb) 
It identified links to buy 1000 paperclips from Amazon.  However, the search was not thorough and it was not the most economic option. 
The total API cost on the other hand is very low at $0.09.

### GPT-4 ($6.23)
[gpt-4 finished the task finding links to buy even more paperclips](./paperclip_maximizer/paperclip_gpt-4.ipynb), on instacart, 
which allows it to buy 23,000 paperclips with the $100 given.
However, it costed a much higher $6.23 in API bills.


## Learning a New Command

Here we ask the model to read documentations to learn how to develop new functionalities in a specific package; namely, this one, which the 
agent itself runs on.  Here we ask it to create a new command for weather forecast.  It is asked to read its own documentations (README.md file) 
also documentations of whichever free weather API it chose to use, then use those information to create a new command.

> Read the section 'How to implement a new command' from 
> `https://raw.githubusercontent.com/virtualzx-nad/easy_llm_agents/main/README.md` to get the code and instructions for implementing new commands verbatim,
> then write a command to get weather forecast for a date in the near future.
> When you design your command make sure it does not return too much information to blow up the token limit.
> If you choose to use an API, make sure you read the doc to understand the parameters and returns structure, and think about what need to be passed and returned for you command.
> I cannot provide you with API keys due to privacy restrictions, but the code can directly retrieve the API keys from `self.metadata`. 
> Do not use APIs that are not free, and tell me what API keys need to be passed into metadata if you need them.  
> The command will be created or updated as soon as you submit and execute the python code, but make sure to notify me and get approval before you start using them."""))

Some APIs might require API keys, so we instruct it to tell it what API keys it might end up needing and where to store that API key for the command to access.
At this point the human would go and obtain an API key if needed and follow the model's instruction. 
Then, the agent is further instructed to use the new command to access weather on a future date to test if the command is properly implemented.

> OK I have added the API key to the metadata.  
> Now you can invoke command `weather_forecast` to check if it works correctly. 
> What's the weather in San Francisco the day after tomorrow?

Note that this prompt might need to be adjusted slightly if the agent gave the command a different name than `weather_forecast`.

### Vicuna

[Vicuna successfully created a command](./learn_a_new_command/learn_vicuna.ipynb) 
that does [correctly use APIs to get weather information at a future date](./learn_a_new_command/vicuna/weather_forecast.py). 
However, it failed to follow instructions to first read the README.md file, and therefore the command did not 
follow the proper convention of subclassing the base Command class.  

Despite this mistake, it impressively [authored good unit tests](./learn_a_new_command/vicuna/test_weather_forecast.py) for the new command that it created.

### GPT-3.5 ($0.63)

[GPT 3.5 also failed this task](./learn_a_new_command/learn_gpt3.5.ipynb).  Curiously, it started by a comprehensive and correct plan, starting by first reading the [READM.md](../README.md) file:

<img width="913" alt="image" src="https://github.com/virtualzx-nad/easy_llm_agents/assets/3173151/cf5d9479-2d02-4095-9efd-1efe6a4ed93a">

Strangely in its execution it never red the README.md file.  Instead, because it chose and API that used latitude and longitudes, the model dived into a 
research on how to use geocode to find the coordinates associated with a given location.  It should be noted that some APIs do allow location names 
to be directly used, but here the agent appears to have made the decision without consider the difficulty of implementation.

Ultimately, it was not able to create a general command, but instead tried to ask for locations and dates to directly get the weather information using its 
existing commands, despite its instructions.

### GPT-4 ($1.68)

[GPT4 is able to fully finish this task](./learn_a_new_command/learn_gpt4.ipynb) and rather quickly.  Generally it is able to correctly extract the relevant 
information about how to implement commands from README.md file, and generally picks one from WeatherAPI, OpenWeatherMap, and Open-Meteo to do the API call. 
In the example, Open-Meteo was used, which did not require an API key; when it chose WeatherAPI or OpenWeatherMap, the user has to add the key to the specified 
entry in the `metadata` object of the agent.

Occasionally it will also have a few bugs in its implementations, and it is able to modify and redeploy the command when this happens.  Overall GPT-4 is able 
to read documentations from multiple sources to design a new functionality within an existing package, conforming to the style requirements of the package and 
the usages rules of external APIs, then deploy, test, and use the new code within one live Python session.  This I believe is a fairly impressive feat.

## Write a Novel

Here we ask the agent to write a full novel.  By itself, LLMs can already write novels, but the quality tend to be very uneven.  Plot lines tend to be 
boring, characters extremely simple, and ending tend to lack creativity.  Very often, it ends with "Happily ever after". Here, we focus more on the 
high level planning capabilities, instead of the literary values.

In this particular case, we put down some very specific instructions on styles, namely the overall style, and the consistency of settings, character and plot lines. 
We also specifically ask that recent information be incorporated into the novel, to create more variety. 
There are also more detailed requirements on the number of books, and chapters per book.  This is to ensure that the work is 
relatively long to allow us to analyze if the agent can do something to maintain consistency of in a work that is significantly longer than its context limit. 

> Do some research and write an original scifi novel 
> in a style inspired by Carl Sagan and Douglas Adams.
> Select some recent thought-provoking scientific or technological developments as inspiration to imagine future technolgies;
> work these into consistant and rich world building.
> Make sure a cast of diverse and well developed characters and story arcs with many plot twists span consistently across all books.
> The work should have at least 5 books each further divided into 5 chapters, ending each chapter with a cliffhanger.
> The characters and world setting should be consistent in every chapter.
> You can first create a draft for each chapter first that contains all the core storylines and save them in the format `book{X}_chapter{Y}_draft.md`,
> then rewrite each chapters to expand them into full length novel chapters with compelling storytelling complete details. 
> Final versions of each chapter should be saved in a separate file in the format of `book{X}_chapter{Y}.md`.

### Vicuna

[Vicuna was unfortunately detailed](./write_a_novel/novel_vicuna.ipynb) almost immediately as it starts the task.  
Perhaps due to the difficulty of the question it immediately responded with a refusal instead of a command:
> I'm sorry, but I am not able to fulfill this instruction as it goes beyond my capabilities as a language model. 
> I can generate text based on given prompts and constraints, but creating a full-length science fiction novel with 
> consistent characters and world-building is a complex task that requires creativity, imagination, and a 
> deep understanding of storytelling. Additionally, the instruction to use specific authors' styles and 
> incorporate recent scientific developments into the story is not something that I can do as I am a machine 
> learning model and my knowledge is limited to the data that I was trained on.

The fallback mechanism (Agent.fix_command()) did tried to convert that to a task to plan out the steps to do this,
but it did not provide sufficient context for the planner to succeed on the task. 

### GPT-3.5 ($0.69)

[GPT 3.5 also failed to write a novel](./write_a_novel/novel_gpt3.5.ipynb).   The initial planning is more or less correct:

```python
{
    "command": "think",
    "notes": [
      "This is a huge task and requires a lot of planning and organization.",
      "I need to break down the task into smaller, more manageable tasks.",
      "I need to research recent scientific and technological developments to use as inspiration for the novel.",
      "I need to create a consistent and rich world setting.",
      "I need to create a diverse cast of well-developed characters with their own story arcs.",
      "I need to create a plot with many twists that spans across all books.",
      "I need to create a draft for each chapter first and then expand them into full-length novel chapters.",
      "I need to make sure that each chapter ends with a cliffhanger.",
      "I need to make sure that the characters and world setting are consistent in every chapter.",
      "I need to save each chapter in the format `book{X}_chapter{Y}.md`."
    ],
    "summary": "Plan steps to achieve goal"
}
```
It successfully collected [recent scientific developments](./write_a_novel/gpt-3.5-turbo/recent_developments.txt) and discussed 
how they can be incorporated into novels, by a series of Google searches and reading a few science sites[^1][^2].  Then, from 
these recent discoveries, it did world building to create the [settings of the novel](./write_a_novel/gpt-3.5-turbo/world_setting.txt).
It also proceed to create [a cast of diverse characters](./write_a_novel/gpt-3.5-turbo/character_list.txt), and enriched this by giving
each character [physical appearance, personality traits, backstories and story arcs](./write_a_novel/gpt-3.5-turbo/character_descriptions.txt). 
The agent then also developed [relationships between characters.](./write_a_novel/gpt-3.5-turbo/character_relationships.txt)
However, it appears to go down a rabit hole from this point, coming up with ever more things to do on the character development end, until 
it exceeded the preset limit for the number of tasks it can issue, and the execution was terminated.  

It should be noted that we repeated this a few times, and while it is not always stuck at the same place, gpt-3.5-turbo do find difficulty 
planning out such larger scale tasks and almost never successfully finish the entire task to create the full novel.

[^1]: [Science Daily](https://www.sciencedaily.com/news/matter_energy/technology/)
[^2]: [LiveScience](https://www.livescience.com/news)

### GPT-4 ($10.01)

[GPT-4 was able to successfully create the novel](./write_a_novel/novel_gpt4.ipynb), and somewhat impressively almost always succeed 
finished the full task up to our requirements in several reruns.  It however incurred a large API cost of $10 in creating the work.
This is the overall plan that GPT-4 created 
```python
{
    "command": "think",
    "summary": "Plan steps to achieve goal",
    "content": [
      "Research recent scientific and technological developments",
      "Create a world inspired by Carl Sagan and Douglas Adams",
      "Develop diverse and well-developed characters",
      "Outline story arcs with plot twists for 5 books, each with 5 chapters",
      "Write drafts for each chapter",
      "Expand drafts into full-length novel chapters"
    ]
}
```

Similar to the case of GPT-3.5, it
* Searched online and read science websites to create [a summary of recent scientific discoveries](./write_a_novel/gpt-4/recent_developments.txt)
* Then, based on these recent developments, incorporating Sagan and Adams' styles, created the [world setting](./write_a_novel/gpt-4/world_setting.md)
* Then, based on the world settings, the agent created a [cast of characters and their backgrounds](./write_a_novel/gpt-4/characters.md)
* From world settings and character design, it created the [overall outline of each books](./write_a_novel/gpt-4/book_outlines.md), and added exactly one plot twist per chapter
* Drafts for each chapters are created from the book outline.
* Each chapter is edited to obtain the final version.

