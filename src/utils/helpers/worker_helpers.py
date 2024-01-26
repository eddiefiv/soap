class SingleInstruction():
    def __init__(self, task, action):
        self.task = task
        self.action = action

    def get_action_list(self):
        '''Returns a list of :class:`SingleInstructions`'s'''
        return [self]

class MultiInstruction():
    '''Takes in a list of :class:`SingleInstruction`'s and manages each instruction'''
    def __init__(self, instructions: list[SingleInstruction]):
        self._instructions = instructions

    def get_action_list(self):
        return [single_instruction for single_instruction in self._instructions]