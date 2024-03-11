from enum import Enum

class WorkerTask(Enum):
    SCREENSHOT = 0 # Take a screenshot of a webpage for later inferencing by a vision model
    GOTO = 1
    CLICK = 2
    TYPE = 3

class SingleInstruction():
    def __init__(self, task, action):
        self.task = task
        self.action = action

    def get_action_list(self):
        '''Returns a list of :class:`SingleInstructions`'s'''
        return [self]

    def out(self):
        return (self.task, self.action)

class MultiInstruction():
    '''Takes in a list of :class:`SingleInstruction`'s and manages each instruction'''
    def __init__(self, instructions: list[SingleInstruction]):
        self._instructions = instructions

    def get_action_list(self):
        return [single_instruction for single_instruction in self._instructions]

def reconstruct_single_instruction(instruction_repr):
    return SingleInstruction(task = WorkerTask[instruction_repr['operation'].upper()], action = instruction_repr['action'])

def reconstruct_multi_instruction(instruction_repr):
    instructions = [instruction for instruction in instruction_repr]
    instructions = [reconstruct_single_instruction(instruction) for instruction in instructions]
    return MultiInstruction(instructions = instructions)