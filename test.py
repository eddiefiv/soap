from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain_community.llms.llamacpp import LlamaCpp

from transformers import AutoTokenizer, AutoModelForCausalLM

from llama_cpp import Llama

from src.utils.helpers.constants import *

system_prompt = {"role": "system", "content": SYSTEM_PROMPT_OCR_WIN_LINUX}

messages = [system_prompt]

user_prompt = {"role": "user", "content": "I want to goto the discord main website and take a screenshot of it."}

messages.append(user_prompt)

# tokenizer = AutoTokenizer.from_pretrained("models/openhermes-2.5-mistral-7b.Q5_K_M")
# model = AutoModelForCausalLM.from_pretrained("models/openhermes-2.5-mistral-7b.Q5_K_M")

# tokenized_chat = tokenizer.apply_chat_template(messages, tokenize = True, add_generation_prompt = True, return_tensors = "pt")
# print(tokenized_chat)

llm = Llama(
    model_path = "models/openhermes-2.5-mistral-7b.Q5_K_M.gguf",
    n_gpu_layers = 33,
    n_ctx = 8192,
    n_batch = 256,
    verbose = True
)

#llm.tokenize(bytes(messages))

output = llm.create_completion(
    prompt = CHAT_ML_PROMPT_FORMAT(SYSTEM_PROMPT_OCR_WIN_LINUX, "I want to make a discord bot to run on my machine. It should have 2 slash commands: mainMenu and settingsMenu. Both menus should display a simple embed and 1 red button for deleting the message (closing out the menu)."),
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

print(output['choices'][0]["text"])