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