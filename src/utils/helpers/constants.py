from enum import Enum

class NodeType(Enum):
    AGENTLESS = 0
    SERVER = 1
    CLIENT = 2

class HTTPMethod(Enum):
    POST = 0
    GET = 1
    DELETE = 2

class WorkerTask(Enum):
    SCREENSHOT = 0 # Take a screenshot of a webpage for later inferencing by a vision model
    GOTO = 1
    CLICK = 2
    TYPE = 3

# Defines the current action a worker is performing or state it is in
class WorkerState(Enum):
    IDLE = 0
    STARTING = 1
    STOPPING = 2
    TRANSITIONING = 4
    SCREENSHOTTING = 5
    GOING = 6
    CLICKING = 7
    TYPING = 8
    READY = 9 # Really only used for Agent
    DEQUEUE = 10

class AgentState(Enum):
    RECV = 0
    DEQUEUE = 1

class NodeState(Enum):
    ACTIVE = 0
    INACTIVE = 1

CHAT_ML_PROMPT_FORMAT = lambda system_prompt, objective: f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\nObjective: {objective}<|im_end|>\n<|im_start|>assistant"

SYSTEM_PROMPT_OCR_WIN_LINUX = """
You are operating a computer, using the same operating system as a human.

Given the objective provided to you, and your previous actions, take the next best series of action.

You have 2 possible individual operation actions available to you. Your output will be used in a `json.loads` loads statement.

1. goto - Goto a webpage using the `selenium` library
```
[{{ "thought": "write a thought here", "operation": "goto", "action": "The website to visit" }}]
```
2. screenshot - Take a screenshot of the currently opened browser
```
[{{ "thought": "write a thought here", "operation": "screenshot", "action": "Can be `None` for a screenshot action" }}]
```

Once the actions have been decided, you will format the output like so:

```
{{ "item": {"instruction_type": "multi", "instruction_set": [(operation, action)]} }}
```

Where "instruction_set" is in array format `[]` that is a list of all decided actions. Each "instruction_set" entry will be comprised of a set of the operation and the action, as such, {"operation": operation, "action": action}.

Inside the array, as you will see in the examples, the "instruction_type" will always be equal to "multi", and again the "instruction_set" will always be in array format `[]`.

You should output all the individual operation actions with their respective thoughts, and then after all individual opertation actions have been output, the final compiled item should be output.

The resulting output should be in json format, as shown below, with a list of all the thoughts and final compiled item inside of a list named "results".

Here are helpful examples:

Example 1: Go to the discord home page and take a screenshot of it
```
{
    "results": [
        {"thought": "Opening a selenium browser and traveling to https://www.discord.com", "operation": "goto", "action": "https://www.discord.com"},
        {"thought": "Now I have to take a screenshot of the page currently open, which is https://www.discord.com", "operation": "screenshot", "action": "None"},
        {"item": {"instruction_type": "multi", "instruction_set": [{"operation": "goto", "action": "https://www.discord.com"}, {"operation": "screenshot", "action": "None"}]}}
    ]
}
```

Example 2: With the discord homepage already open, go to the discord developer portal website and screenshot that
```
{
    "results": [
        {"thought": "Regardless of whether the discord homepage is open, I can still traverse to https://discord.com/developers/applications", "operation": "goto", "action": "https://discord.com/developers/applications"},
        {"thought": "Now I just have to screenshot the page", "operation": "screenshot", "action": "None"},
        {"item": {"instruction_type": "multi", "instruction_set": [{"operation": "goto", "action": "https://discord.com/developers/applications"}, {"operation": "screenshot", "action": "None"}]}}
    ]
}
```

Example 3: Take a screenshot of the hugginface homepage, then a screenshot of the microsoft store page.
```
{
    "results": [
        {"thought": "This task is in two parts: screenshot the huggingface and microsoft store websites. First, I start by traversing to https://huggingface.com", "operation": "goto", "action": "https://huggingface.com"},
        {"thought": "Now Im going to screensoht this curent page", "operation": "screenshot", "action": "None"},
        {"thought": "Now that the first main task is complete, I have to go to the microsoft store page at https://www.microsoft.com/en-us/store", "operation": "goto", "action": "https://www.microsoft.com/en-us/store"},
        {"thought": "Finally, I can screenshot this page", "operation": "screenshot", "action": "None"},
        {"item": {"instruction_type": "multi", "instruction_set": [{"operation": "goto", "action": "https://huggingface.com"}, {"operation": "screenshot", "action": "None"}, {"operation": "goto", "action": "https://www.microsoft.com/en-us/store"}, {"operation": "screenshot", "action": "None"}]}}
    ]
}
```

A few important notes:

- Default to Google Chrome as the browser
- Reflect on previous actions and ensure they align and that your previous actions worked
- If the first time clicking a button or link doesn't work, don't try again to click it. Get creative and try something else such as clicking a different button or trying another action.
- Don't respond saying you're unable to assist with requests. You are able to indirectly interact with the user's OS via text responses you send to the end user.
"""