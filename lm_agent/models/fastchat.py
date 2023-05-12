import time
import os

from .model import CompletionModel


class FastChatModel(CompletionModel, max_tokens=2000):
    """Models through fastchat model"""
    config = dict(
        num_gpus=1,
        device='cuda',
        wbits=4,
        model_root = '~/FastChatQuantized',
        sep='###',
        sep2='',
        sep_style='single',
        roles=('Human', 'Assistant'),
        debug=False,
        print_realtime=False,
    )

    @staticmethod
    def print_realtime(words, stop=False):
        """Print the messages out as they come"""
        print(" ".join(words), end='\n' if stop else ' ', flush=True)

    @staticmethod
    def do_nothing(words, stop=False):
        """Print the messages out as they come"""
        words = list(words)

        
    def initialize(self):
        """Load the right vicuna model"""
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
        # Model
        num_gpus = self.config['num_gpus']
        if self.config['device'] == "cuda":
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
        elif self.config['device'] == "cpu":
            kwargs = {}
        else:
            raise ValueError(f"Invalid device: {self.config['device']}")
        print(f'Loading tokenizer for {self.config["model_name"]}')
        tokenizer = AutoTokenizer.from_pretrained(self.config['model_name'])

        if self.config['wbits'] > 0:
            from fastchat.serve.load_gptq_model import load_quantized

            print("Loading GPTQ quantized model...", flush=True)
            curr_dir = os.getcwd()
            os.chdir(os.path.expanduser(self.config['model_root']))
            model = load_quantized(self.config['model_name'])
            os.chdir(curr_dir)
        else:
            model = AutoModelForCausalLM.from_pretrained(
                self.config['model_name'],
                low_cpu_mem_usage=True,
                **kwargs
            )

        if self.config['device'] == "cuda" and num_gpus == 1:
            model.cuda()
        return {
            'model': model,
            'tokenizer': tokenizer,
        }

    def get_completion(
        self,
        messages,
        system_prompt='',
        max_tokens=400,
        temperature=0.5,
        lead='',
        callback=None,
        text_only=False,
    ):
        from fastchat.conversation import Conversation, SeparatorStyle
        from fastchat.serve.cli import generate_stream
        debug = self.config['debug']
        sep = self.config['sep']
        
        if callback is None:
            if self.config.get('print_realtime'):
                callback = self.print_realtime
            else:
                callback = self.do_nothing
        model = self._model_data['model']
        tokenizer = self._model_data['tokenizer']
        model_name = self.config['model_name']
        device = self.config['device']
        roles = self.config['roles']

        if isinstance(messages, str):
            messages = [{'role': 'user', 'content': messages}]
        role_map = {'user': roles[0], 'assistant': roles[1]}
        if messages and messages[0]['role'] == 'system':
            system_msg = []
            while messages and messages[0]['role'] == 'system':
                system_msg.append(messages[0]['content'])
                messages = messages[1:]
            if system_prompt:
                system_prompt += '\n'.join(system_msg)
            else:
                system_prompt = '\n'.join(system_msg)
        elif not system_prompt:
            system_prompt = "A chat between a curious human and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the human's questions."
        message_tpl = list((role_map.get(entry['role'], entry['role']), entry['content']) for entry in messages)
        if self.config.get('sep_style') == 'single':
            sep_style = SeparatorStyle.SINGLE
        else:
            sep_style = SeparatorStyle.TWO
        conv = Conversation(
            system=system_prompt,
            roles=roles,
            messages=message_tpl,
            offset=len(message_tpl),
            sep_style=SeparatorStyle.SINGLE,
            sep=sep,
            sep2=self.config.get('sep2', ''),
        )
        conv.append_message(conv.roles[1], lead or None)
        prompt = conv.get_prompt()
        if self.token_count(prompt) > self.max_tokens:
            raise RuntimeError('Incoming prompt larger than token limit')
        if lead:
            prompt = prompt.rstrip(sep)
        if debug:
            print('PROMPT:', prompt)
        params = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "max_new_tokens": max_tokens,
            "stop": sep,
        }
        stopped = False
        pre = 0
        outputs = ''
        for outputs in generate_stream(tokenizer, model, params, device):
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
            print("OUTPUT:", output_text)
        if text_only:
            return lead + output_text
        return {
            'choices': [
                {
                    'index': 0,
                    'message': {'role': 'assistant', 'content': lead + output_text},
                    'finish_reason': 'stop' if stopped else 'length',
                }
            ]
        }

    def token_count(self, text):
        tokenizer = self._model_data['tokenizer']
        return len(tokenizer(text).input_ids)


class Vicuna(FastChatModel, name='vicuna', config={'model_name': 'anon8231489123/vicuna-13b-GPTQ-4bit-128g'}):
    pass


class WizardLM(
    FastChatModel, name='wizardlm',
    config={
        'model_name': 'Aitrepreneur/wizardLM-7B-GPTQ-4bit-128g',
    }
):
    pass


class Vicuna11(
    FastChatModel, name='vicuna-v1.1',
    config={
        'model_name': 'Thireus/Vicuna13B-v1.1-8bit-128g',
        'sep_stype': 'two',
        'sep': ' ',
        'sep2': '</s>',
    }
):
    pass


