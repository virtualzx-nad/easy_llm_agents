from .openai import get_openai_completion


MODEL_SWITCH = {
    'gpt-3.5-turbo': get_openai_completion,
    'gpt-4': get_openai_completion,
    'gpt-4-32k': get_openai_completion,
}

def get_completion(message, model='gpt-3.5-turbo', *args, **kwargs):
    """Generic completion for different model vendors"""
    if model not in MODEL_SWITCH:
        raise ValueError(f'Unrecognized model {model}')
    completion_func = MODEL_SWITCH[model]
    return completion_func(message, *args, model=model, **kwargs)