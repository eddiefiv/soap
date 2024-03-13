import json
import console
import os

CURRENT_DURECTORY = os.path.dirname(os.path.abspath(__file__))

# Navigate to the parent directory (Corporate America) relative to the script's directory
PARENT_DIRECTORY = os.path.abspath(os.path.join(CURRENT_DURECTORY, os.pardir, os.pardir))

# Navigate to the config directory relative to the script's directory
CONFIG_DIRECTORY = os.path.join(PARENT_DIRECTORY, 'config')

# Path to the global.jsoon file relative to the script's directory
GLOBAL_CONFIG_FILE_PATH = os.path.join(CONFIG_DIRECTORY, 'config.json')

CONFIG_FILE_DEFAULT_CONTENTS = {
    "general": {
        "agent_count": 2,
        "worker_count": 3
    },
    "llama_cpp_settings": {
        "70b": {
            "filepath": None,
            "ctx_size": 2048,
            "gpu_layer_count": 41,
            "batch_size": 512
        },
        "13b": {
            "filepath": None,
            "ctx_size": 2048,
            "gpu_layer_count": 21,
            "batch_size": 512
        },
        "7b": {
            "filepath": "openhermes-2.5-mistral-7b.Q5_K_M.gguf",
            "ctx_size": 2048,
            "gpu_layer_count": 33,
            "batch_size": 512
        },
        "hyperparams": {
            "temperature": 0.7,
            "max_tokens": 3000,
            "top_p": 0.92,
            "min_p": 0.05,
            "repeat_penalty": 1.1,
            "presence_penalty": 1.0,
            "top_k": 100,
            "microstat_eta": 0.1,
            "microstat_tau": 5
        }
    }
}

console.print_info("Generating default config.json...")

if os.path.exists(GLOBAL_CONFIG_FILE_PATH):
    console.print_warning("Existing config.json file found, would you like to overwrite? (Y/N)")

    if input().lower() == "y":
        with open(GLOBAL_CONFIG_FILE_PATH, "w") as f:
            f.write(json.dumps(CONFIG_FILE_DEFAULT_CONTENTS,indent = 4))
    else:
        quit(1)
else:
    with open(GLOBAL_CONFIG_FILE_PATH, "w") as f:
            f.write(json.dumps(CONFIG_FILE_DEFAULT_CONTENTS, indent = 4))
console.print_success(f"Default config successfully written to {CONFIG_DIRECTORY}. Ensure you use the --config flag when running client_node.py to use the new config.")