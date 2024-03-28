import json

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain_community.llms.llamacpp import LlamaCpp

from transformers import AutoTokenizer, AutoModelForCausalLM, LlamaTokenizer

from llama_cpp import Llama

from src.utils.helpers.constants import *

tokenizer = AutoTokenizer.from_pretrained("NousResearch/Nous-Hermes-Llama2-13b")

print(tokenizer.all_special_tokens)
print(tokenizer.eos_token)

quit(0)

#system_prompt = {"role": "system", "content": SYSTEM_PROMPT_OCR_WIN_LINUX}
system_prompt = {"role": "system", "content": "You are a professional emailer, your job is to read over the emails I give you and provide a response given my criteria."}
messages = [system_prompt]

d = """
These are the problems I'm planning to post today, take a look at them and let me know if you think they're ranked properly. I have solutions for them as well if you need it.

Easy:
https://leetcode.com/problems/concatenation-of-array/submissions/1188846766/

Medium:
https://www.hackerrank.com/challenges/string-validators/problem?isFullScreen=true

Hard:
https://leetcode.com/problems/palindrome-number/

Thank you

Can you come up with a short response to this email.
"""

user_prompt = {"role": "user", "content": d}

messages.append(user_prompt)

# tokenizer = AutoTokenizer.from_pretrained("models/openhermes-2.5-mistral-7b.Q5_K_M")
# model = AutoModelForCausalLM.from_pretrained("models/openhermes-2.5-mistral-7b.Q5_K_M")

# tokenized_chat = tokenizer.apply_chat_template(messages, tokenize = True, add_generation_prompt = True, return_tensors = "pt")
# print(tokenized_chat)

def load_model():
    llm = Llama(
        model_path = "models/openhermes-2.5-mistral-7b.Q5_K_M.gguf",
        n_gpu_layers = 33,
        n_ctx = 8192,
        n_batch = 256,
        verbose = True
    )

    return llm

#llm.tokenize(bytes(messages))

def inference_model(model):
    output = model.create_completion(
        prompt = CHAT_ML_PROMPT_FORMAT(SYSTEM_PROMPT_WIN_LINUX_AGENT, "Develop a comprehensive crypto trading bot system. Design and implement a framework capable of interfacing with the DyDx API for price data and integrating the DyDx API for trading functionalities. Incorporate watchlist functionality into the trading bot. Develop placing functionality to analyze market conditions and execute buy/sell orders based on predefined strategies. Implement closing functionality to monitor and manage open positions according to predefined criteria such as profit targets or stop-loss levels."),
        temperature = 0.7,
        max_tokens = 16000,
        top_p = 0.92,
        min_p = 0.05,
        repeat_penalty = 1.1,
        presence_penalty = 1.0,
        top_k = 100,
        mirostat_eta = 0.1,
        mirostat_tau = 5
    )

    return output['choices'][0]["text"]

try:
    model = load_model()
    out = inference_model(model)
    if out is not None:
        if type(out) == str:
            out = json.loads(out)
    else:
        print(f"This returned None during inference. No output from model was recevied.")

    # Take the output and verify it is in the proper format
    if 'item' in out:
        print(out)
    else:
        print(f"Model output not of desired type. {type(out)}\n\n-- Output --\n{out['choices'][0]['text']}\n\nCurrent instruction is being negated.")
except Exception as e:
    print(f"This: An error occurred while loading LLM. Current instruction is being negated. {repr(e)}")