import json

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