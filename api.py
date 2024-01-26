import requests
import json

host = "http://localhost:5001"

body = {
    "dynatemp_range": 0,
    "logit_bias": {},
    "max_context_length": 4096,
    "max_length": 512,
    "memory": "",
    "n": 1,
    "presence_penalty": 0,
    "prompt": "\n### Instruction:\nWrite me a python file that will create a get request with localhost on port 5001? Only write code, don't generate any extra text or anything else. Don't include code formatting or any markdown in the response. Just simply write the code as it would be written by a human.\n### Response\n",
    "quiet": True,
    "rep_pen": 1.1,
    "rep_pen_range": 320,
    "rep_pen_slope": 0.7,
    "temperature": 0.7,
    "sampler_order": [6, 0, 1, 3, 4, 2, 5],
    "stop_sequence": ["### Instruction:", "### Response:"],
    "tfs": 1,
    "top_a": 0,
    "top_k": 100,
    "min_p": 0,
    "top_p": 0.92,
    "typical": 1
}

r = requests.post(host + "/api/v1/model", data = json.dumps(body)).json()

print(r)

with open("output.py", "w") as f:
    lines = r['results'][0]['text'].splitlines()

    for line in lines:
        f.write(f"{line}\n")