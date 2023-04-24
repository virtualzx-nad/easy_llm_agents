import time
import os

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

from fastchat.conversation import Conversation, SeparatorStyle
from fastchat.serve.cli import generate_stream


MODEL_REGISTRY = {}


def print_realtime(words, stop=False):
    """Print the messages out as they come"""
    print(" ".join(words), end='\n' if stop else ' ', flush=True)

def register_model(
    alias,
    model_name='anon8231489123/vicuna-13b-GPTQ-4bit-128g',
    num_gpus=1, device='cuda', wbits=4,
    model_root='~/FastChatQuantized',
):
    """Load the right vicuna model"""
    # Model
    if device == "cuda":
        kwargs = {"torch_dtype": torch.float16}
        if num_gpus == "auto":
            kwargs["device_map"] = "auto"
        else:
            num_gpus = int(num_gpus)
            if num_gpus != 1:
                kwargs.update({
                    "device_map": "auto",
                    "max_memory": {i: "13GiB" for i in range(num_gpus)},
                })
    elif device == "cpu":
        kwargs = {}
    else:
        raise ValueError(f"Invalid device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    if wbits > 0:
        from fastchat.serve.load_gptq_model import load_quantized

        print("Loading GPTQ quantized model...", flush=True)
        curr_dir = os.getcwd()
        os.chdir(os.path.expanduser(model_root))
        model = load_quantized(model_name)
        os.chdir(curr_dir)
    else:
        model = AutoModelForCausalLM.from_pretrained(model_name,
            low_cpu_mem_usage=True, **kwargs)

    if device == "cuda" and num_gpus == 1:
        model.cuda()
    if alias:
        MODEL_REGISTRY[alias] = {
            'model': model,
            'name': model_name,
            'tokenizer': tokenizer,
            'device': device
        }
    return model
    
def get_vicuna_completion(
    messages,
    model,
    max_new_tokens=500,
    temperature=0.5,
    roles=None,
    sep='###',
    debug=False,
    callback=None,
    text_only=False,
    model_root='~/FastChatQuantized',
):
    entry = MODEL_REGISTRY[model]
    if isinstance(messages, str):
        messages = [{'role': 'user', 'content': messages}]
    model_ref = entry['model']
    model_name = entry['name']
    tokenizer = entry['tokenizer']
    device = entry['device']
    roles = roles or ('Human', 'Assistant')
    role_map = {'user': roles[0], 'assistant': roles[1]}
    if messages and messages[0]['role'] == 'system':
        system_msg = []
        while messages[0]['role'] == 'system':
            system_msg.append(messages[0]['content'])
            messages = messages[1:]
        system_prompt = '\n'.join(system_msg)
    else:
        system_prompt = "A chat between a curious human and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the human's questions."
    message_tpl = list((role_map.get(entry['role'], entry['role']), entry['content']) for entry in messages)
    # create conversation
    conv = Conversation(
        system=system_prompt,
        roles=roles,
        messages=message_tpl,
        offset=len(message_tpl),
        sep_style=SeparatorStyle.SINGLE,
        sep=sep,
    )
    conv.append_message(conv.roles[1], None)
    prompt = conv.get_prompt()

    params = {
        "model": model_ref,
        "prompt": prompt,
        "temperature": temperature,
        "max_new_tokens": max_new_tokens,
        "stop": sep,
    }
    stopped = False
    pre = 0
    for outputs in generate_stream(tokenizer, model_ref, params, device):
        if isinstance(outputs, list):
            outputs = outputs[0]
            stopped = True
        outputs = outputs[len(prompt) + 1:].strip()
        outputs = outputs.split(" ")
        now = len(outputs)
        if now - 1 > pre:
            if callable(callback):
                callback(outputs[pre:now-1], stop=False)
            pre = now - 1
    if callable(callback):
        callback(outputs[pre:], stop=True)

    output_text = " ".join(outputs)
    if debug:
        print("\n", {"prompt": prompt, "outputs": outputs}, "\n")
    if text_only:
        return output_text
    return {
        'choices': [
            {
                'index': 0,
                'message': {'role': 'assistant', 'content': output_text},
                'finish_reason': 'stop' if stopped else 'length',
            }
        ]
    }



register_model('vicuna')