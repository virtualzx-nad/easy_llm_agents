from .openai import get_openai_completion, get_openai_edit
try:
    from .vicuna import get_vicuna_completion
    has_vicuna = True
except ImportError:
    pass

MODEL_SWITCH = {
    'gpt-3.5-turbo': get_openai_completion,
    'gpt-4': get_openai_completion,
    'gpt-4-32k': get_openai_completion,
}
if has_vicuna:
    MODEL_SWITCH['vicuna'] = get_vicuna_completion

def get_completion(message, model='gpt-3.5-turbo', *args, **kwargs):
    """Generic completion for different model vendors"""
    if model not in MODEL_SWITCH:
        raise ValueError(f'Unrecognized model {model}')
    completion_func = MODEL_SWITCH[model]
    return completion_func(message, *args, model=model, **kwargs)



EDIT_MODEL_SWITCH = {
    'code-davinci-edit-0001': get_openai_edit,
    'text-davinci-edit-0002': get_openai_edit,
}
def get_edit(text, instruction, model='text-davinci-edit-0002', *args, **kwargs):
    """Generic edit for different model vendors"""
    if model not in EDIT_MODEL_SWITCH:
        raise ValueError(f'Unrecognized edit model {model}')
    edit_func = EDIT_MODEL_SWITCH[model]
    return edit_func(text, instruction, *args, model=model, **kwargs)


