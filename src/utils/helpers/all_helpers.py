import json

from llama_cpp import Llama

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

def load_model(model_path, n_gpu_layers = 41, n_ctx = 2048, n_batch = 256):
    try:
        llm = Llama(
            model_path = model_path,
            n_gpu_layers = n_gpu_layers,
            n_ctx = n_ctx,
            n_batch = n_batch
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
            mirostat_eta = hyperparams['mirostat_eta'],
            mirostat_tau = hyperparams['mirostat_tau']
        )

        return output['choices'][0]["text"]
    except:
        return None