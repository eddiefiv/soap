import json
import jsonpickle
import websockets
import asyncio
import multiprocessing
import time
import os

from multiprocessing import Queue

from agent import Agent

from utils.helpers.constants import *
from utils.helpers.all_helpers import create_ws_message, load_model, inference_model
from utils.console import *

from platform import system, node, version, machine, processor
from socket import gethostname
from psutil import virtual_memory, cpu_count

class Node():
    '''Defines a single device that can either be an agentless server, or a client with `n` agents.
    A :class:`Node` manages each of its agents and the communication between the server and other clients.
    A server :class:`Node` MUST be initialized before clients can connect and being working their :class:`Agents`.
    A machine can NOT have more than one :class:`Node` running on it.
    :class:`Node`'s server a localhost that all :class:`Agent`'s and :class:`Worker`'s communicate through'''

    agents = [] # A lits of all attached agents

    def __init__(self, ntype: NodeType, max_agents: int):
        self._node_type = ntype
        self._max_agents = max_agents
        self.ready = False # Defines whether the node is ready to receive instruction or not
        self.agent_task_queue = Queue()
        self.node_name = f"Node-{gethostname()}"

        self.agents = []

    def set_metrics_config(self):
        d = {
            node(): {
                "system": system(),
                "version": version(),
                "machine": machine(),
                "processor": processor(),
                "hostname": gethostname(),
                "total_virtual_memory": round(virtual_memory().total / (1024.0 **3), 2),
                "cpu_count": cpu_count()
            }
        }

        # Get the directory of the script being executed
        current_directory = os.path.dirname(os.path.abspath(__file__))

        # Navigate to the parent directory (Corporate America) relative to the script's directory
        parent_directory = os.path.abspath(os.path.join(current_directory, os.pardir))

        # Navigate to the config directory relative to the script's directory
        config_directory = os.path.join(parent_directory, 'config')

        # Path to the node_metrics.json file relative to the script's directory
        node_metrics_file_path = os.path.join(config_directory, 'node_metrics.json')

        # Path to the global.jsoon file relative to the script's directory
        global_config_file_path = os.path.join(config_directory, 'global.json')

        # Path to the models folder where all local models are stored
        models_folder_path = os.path.join(parent_directory, 'models')

        try:
            print_debug(node_metrics_file_path)
            with open(node_metrics_file_path, "w") as f:
                f.write(json.dumps(d, indent = 4))
            print_success("Node metrics file up to date.")
        except Exception as e:
            print_warning(text = f"Node couldnt update metrics config. Directory may not exist.")

        try:
            with open(global_config_file_path, 'r') as f:
                _r = f.read()
                self.global_config = json.loads(_r)

                # Set the model folder location in the config
                self.global_config['models_folderpath'] = models_folder_path
            print_success("Global configs successfully loaded.")
        except Exception as e:
            print_error(text = f"Node couldnt load and set configs from config.json, resorting to default configs.")
            self.global_config = {
                "general": {
                    "agent_count": 2,
                    "worker_count": 3
                },
                "models": {
                    "70b_filepath": None,
                    "13b_filepath": None,
                    "7b_filepath": None
                },
                "dev": {
                    "debug_mode": True
                }
            }

    async def listen(self):
        '''Begin listening to the localhost WebSocket'''
        async with websockets.connect("ws://localhost:5002") as ws:
            self.ws = ws
            print_step(f"Node on {gethostname()} started!", justification = "center", style = "green1")
            self.ready = True

            while True:
                res = await ws.recv()
                res = json.loads(res)
                #print_debug(f"{self.node_name}: {res}")
                await self._parse(res) # TODO: Create new process on each parse. Processes will autokill after completion, no need to .join()

    async def inference(self):
        '''Inferences the LLM with the main prompt that is then to be split up into tasks amongst the :class:`Agent`'s'''
        pass

    async def _parse(self, msg):
        if msg['target'] == self.node_name or msg['target'] == "any_node":
            if msg['type'] == "function_invoke":
                if msg['data']['function_to_invoke'] == "attach_agent": # Specific bc of the way the parameters are serialized
                    _params = msg['data']['params']
                    await self.attach_agent(uses_inference_endpoint = _params['uses_inference_endpoint'], inference_endpoint = _params['inference_endpoint'], uid = jsonpickle.decode(_params['uid']))
            elif msg['type'] == "new_instruction":
                # Inference the incoming instruction and parse it down into smaller bits to then be added to the Agent Task Queue
                ins = msg['data']['instruction']

                # Parse and send the prompt to the model to be inferenced
                try:
                    model = load_model(os.path.join(self.global_config['models_folderpath'], self.global_config['llama_cpp_settings']['7b']['filepath']))
                    out = inference_model(model, CHAT_ML_PROMPT_FORMAT, SYSTEM_PROMPT_OCR_WIN_LINUX, ins, self.global_config['llama_cpp_settings']['hyperparams'])
                    if out is not None:
                        out = json.loads(out)

                    print(out)

                    # Take the output and verify it is in the proper format
                    if 'item' in out['results'][-1]:
                        # Let the server know and begin to add the item to the queue (yes the message is being sent back to this Node)
                        await self.ws.send(create_ws_message(type = "node_add_queue_item", origin = self.node_name, target = self.node_name, data = out['results'][-1]))
                    else:
                        print_error(f"{self.node_name}: Model output not of desired type.\n\n-- Output --\n{out}\n\nCurrent instruction is being negated.")
                except:
                    print_error(f"{self.node_name}: An error occurred while loading LLM. Current instruction is being negated.")
            elif msg['type'] == "node_add_queue_item":
                # Add item to queue
                self.agent_task_queue.put(msg['data'])

                # Tell all agents to dequeue if they arent already
                for agent in self.all_recv_agents():
                    print(agent)
                    _idx = self.find_agent_idx_from_name(agent['name'])
                    if _idx is not None:
                        self.agents[_idx]['state'] = AgentState.DEQUEUE.value
                    await self.ws.send(create_ws_message(type = "agent_dequeue", origin = self.node_name, target = agent['name']))
            elif msg['type'] == "agent_ready":
                _idx = self.find_agent_idx_from_name(msg['origin'])
                if _idx is not None:
                    self.agents[_idx]['state'] = AgentState.DEQUEUE.value
                await self.ws.send(create_ws_message(type = "agent_dequeue", origin = self.node_name, target = msg['origin']))
            elif msg['type'] == "agent_complete":
                # If there is more tasks in the Agent Task Queue, then re-dequeue the Agent, otherwise keep it on recv mode
                _idx = self.find_agent_idx_from_name(msg['origin'])
                if _idx is not None:
                    self.agents[_idx]['state'] = AgentState.RECV.value
                if not self.agent_task_queue.empty():
                    if _idx is not None:
                        self.agents[_idx]['state'] = AgentState.DEQUEUE.value
                    await self.ws.send(create_ws_message(type = 'agent_dequeue', origin = self.node_name, target = msg['origin']))
            elif msg['type'] == "agent_dequeue_success":
                # If there is more tasks in the Agent Task Queue, then re-dequeue the Agent, otherwise keep it on recv mode
                _idx = self.find_agent_idx_from_name(msg['origin'])
                if _idx is not None:
                    self.agents[_idx]['state'] = AgentState.DEQUEUE.value
                if not self.agent_task_queue.empty():
                    await self.ws.send(create_ws_message(type = "agent_dequeue", origin = self.node_name, target = msg['origin']))
            return False
        return False

    def all_recv_agents(self):
        _recv_agents = []

        for agent in self.agents:
            if agent['state'] == AgentState.RECV.value:
                _recv_agents.append(agent)
        print(_recv_agents)
        return _recv_agents

    def find_agent_idx_from_name(self, name):
        '''Tries to find an entry in self.agents matching the given name. Returns None if nothing is found'''
        for i in range(len(self.agents)):
            if self.agents[i]['name'] == name:
                return i
        return None

    async def attach_agent(self, uses_inference_endpoint = True, inference_endpoint = "http://localhost:5001", uid = ""):
        '''Attaches an agent to this :class:`Node`. No more agents can be added that exceed the `max_agents` count.'''
        _new_agent = Agent(self.global_config, parent_node_name = self.node_name, uses_inference_endpoint = uses_inference_endpoint, inference_endpoint = inference_endpoint, uid = uid, agent_task_queue = self.agent_task_queue)
        if len(self.agents) < self._max_agents: # If there is still room for more agents
            print_substep(f"NODE: Adding Agent: {_new_agent}", style = "bright_blue")
            self.agents.append({"name": _new_agent.agent_name, "state": AgentState.RECV.value}) # Add agent to a list of agents. List length contains the amount of currently attached agents
            _p = multiprocessing.Process(target = _new_agent.sync_start, name = f"Process-{_new_agent.agent_name}")
            _p.start() # Start the new agent process
        else:
            print_warning("Max agents for this node has already been reached")