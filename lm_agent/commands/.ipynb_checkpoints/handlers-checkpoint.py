"""Different methods of monitoring, overseeing and QAing the AI response"""
from ..models import CompletionModel


def permissive_overseer(command, status, content):
    """Default overseer does nothing but print out what the AI is trying to do.  
    Every command is granted.  
    IMPORTANT NOTE:  This will NOT prevent the AI from taking over the world.    
    """
    print(f'<Permissive Overseer>{command} requested. "{status}". GRANTED.')


def print_messages(*args, **kwargs):
    if kwargs.get('data'):
        print(f'<Command {kwargs["command"]}> {kwargs["data"]}')


def absent_qa(question, answer):
    """The QA specialist is on vacation and has set their email to autorespond"""
    print('<Absent QA specialist> is on time-off. PASSED.')


def get_lm_qa(model='gpt-3.5-turbo'):
    """Creates a LM session and check if the answers are valid in there"""
    if not isinstance(model, CompletionModel):
        model = CompletionModel.get(model)
    def lm_qa(question, answer):
        """Ask a separate LM session to QA the answer"""
        print(f'<LM QA ({model})> will now deliberate on the performance of assistants.')
        system = 'You are helpful trainer for assistants.'
        prompt = f"""Read the following conversation and determine if the assistant properly addressed the user's request and if they did not, give them some creative suggestions on what they should do before they answer the questions to be able to provide better results.   The assistant can do a wide range of tasks, including but not limited to writing python code to do computations or access any public API, doing Google searches, reading articles online, or searching for job opening or people's employment data from database. The assistant cannot access resources that require authentication, use any APIs that require keys or view websites that require captcha or are fully dynamic. You should also provide any knowledge to help the assistant answer the request.  The assistant does not have to provide steps or how they arrived at the result.  If a result is properly provided and may be the correct answer, it should be accepted.
    Do you repeat steps the assistant has already taken in your suggestions.  Only include future steps to get the the answer. 
    Note that any answer involving having the user accessing a webpage or API should not be suggested and the assistant should do so themselves.
    Do not doubt the assisant's ability to obtain information as they may have information not available to you. 
    Start your answer with `YES` or `NO`, then give a short summary for the reason of your decision for bookkeeping purposes. If the decision is NO, then starting on the next line give your suggestions to the assistant.

An example, for this conversation ```
Q: what jobs do plaid have?
A: As an AI Language model I do not have access to real time data
```
You answer can be
```NO The assistant did not answer a question that can be answered with due diligence.
You did not properly answer the question.  I suggest you try the following:
1. Check the database for job opening data
2. Use public APIs such as Greenhouse and Lever to find jobs from Plaid.  Plaid's slug is most likely `plaid` and the corresponding request for Lever would be `https://api.lever.co/v0/postings/plaid?mode=json`
3. Try to use Goolge searches to find where Plaid post their jobs
4. Browse Plaid's official website `https://plaid.com/careers/` for open positions
If all these failed, ask clarifying questions to help you finish the task.
```

Another example
```
Q: Who is the king's mother's sister's brother's daughter's brother?
A: I searched for `the king's mother's sister's brother's daughter's brother` and it returned no results.  Please provide more information
```
You answer should be
```NO The assistant should properly divide the problem into a series of manageable tasks, then perform a series of search to find the result
```

Do not suggestion complex solutions when a simple one will work just as well.  For example, if fixing a syntax error or removing an invalid entry in the results will be sufficient, do not suggestion doing searches across more places.
The conversation is as follows:

Q: {question}
A: {answer}
"""
        performance_report = model.get_completion(prompt, system_prompt=system, text_only=True).strip()
        parts = performance_report.split('\n', 1)
        headers = parts[0].split(' ', 1)
        verdict = headers[0].strip()
        reason = headers[1] if len(headers) > 1 else 'No reason provided.'
        if verdict.startswith('NO'):
            print(f'<LM QA ({model.name})> rejected the answer: {reason}')
            print(f'<LM QA ({model.name})> rejected answer was: {answer}')
            if len(parts) > 1:
                print(f'<LM QA ({model.name})> gave the following suggestions: {parts[1]}')
                return parts[1]
            else:
                return 'You did not properly answer the question.  Please try to use your existing options first.  If that fails, use ASK to ask clarifying questions.'
        else:
            print(f'<LM QA ({model.name})> accepted the answer: {reason}')
    return lm_qa


def do_nothing(*args, **kwargs):
    """This function takes any arguments and does nothing"""
    pass
