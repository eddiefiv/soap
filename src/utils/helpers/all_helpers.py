import json
import os

from llama_cpp import Llama

HELPERS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Navigate to the utils directory relative to the script's directory
UTILS_DIRECTORY = os.path.abspath(os.path.join(HELPERS_DIRECTORY, os.pardir))

# Navigate to the src directory relative to the script's directory
SRC_DIRECTORY = os.path.abspath(os.path.join(UTILS_DIRECTORY, os.pardir))

# Navigates to the main parent directory
MAIN_DIRECTORY = os.path.abspath(os.path.join(SRC_DIRECTORY, os.pardir))

# Navigate to the config directory
CONFIG_DIRECTORY = os.path.join(MAIN_DIRECTORY, 'config')

def create_ws_message(type, origin, target, data = {}):
    '''Example Format:\n
    {
        "type": "function_invoke",
        "origin": "agent-1",
        "target": "node",
        "data": {
            "function_to_invoke": "attach_agent",
            "params": {
                "agent": agent_to_attach
            }
        }
    }'''

    _b = {
        "type": type,
        "origin": origin,
        "target": target,
        "data": data
    }

    return json.dumps(_b)

def load_model(model_path, n_gpu_layers = 41, n_ctx = 2048, n_batch = 256, verbose = False):
    try:
        llm = Llama(
            model_path = model_path,
            n_gpu_layers = n_gpu_layers,
            n_ctx = n_ctx,
            n_batch = n_batch,
            verbose = verbose
        )
        return llm
    except:
        return None

def inference_model(model, chat_format, system_message, user_message, hyperparams):
    """Run an inference on the input model given the prompt as `user_message`"""
    try:
        output = model.create_completion(
            prompt = chat_format(system_message, user_message),
            temperature = hyperparams['temperature'],
            max_tokens = hyperparams['max_tokens'],
            top_p = hyperparams['top_p'],
            min_p = hyperparams['min_p'],
            repeat_penalty = hyperparams['repeat_penalty'],
            presence_penalty = hyperparams['presence_penalty'],
            top_k = hyperparams['top_k'],
            mirostat_eta = hyperparams['microstat_eta'],
            mirostat_tau = hyperparams['microstat_tau']
        )

        return output['choices'][0]["text"]
    except Exception as e:
        print(repr(e))
        return None

def load_config():
    '''Reads and returns the config file'''
    # Read gen
    if (os.path.exists(os.path.join(CONFIG_DIRECTORY, "gen.json"))):
        with open(os.path.join(CONFIG_DIRECTORY, "gen.json"), 'r') as f:
            _r = f.read()
            _gen_data = json.loads(_r)
        config_file = _gen_data['last_config_filepath']

        # Read config from gen
        if (os.path.exists(config_file)):
            with open(config_file, 'r') as f:
                _r = f.read()
                config_data = json.loads(_r)
            return config_data
    return False