import json
import os
import requests

def get_inference_config():
    if os.getcwd().endswith("src"):
        try:
            with open("../config/inference_configs.json", "r") as f:
                _data = f.read()
                _loaded = json.loads(_data)
            return _loaded
        except:
            print("File not found in /config directory")

            return None
    else:
        try:
            with open(".../config/inference_configs.json", "r") as f:
                _data = f.read()
                _loaded = json.loads(_data)
            return _loaded
        except:
            print("File not found in /config directory")

            return None

def validate_endpoint(endpoint):
    '''Ensures an endpoint is reachable. If not, returns `False`.'''

    try:
        r = requests.get(endpoint)
        return True
    except Exception as e:
        return False