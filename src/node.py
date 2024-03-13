import json
import jsonpickle
import websockets
import multiprocessing
import os
import requests

from multiprocessing import Queue

from agent import Agent

from utils.helpers.constants import *
from utils.helpers.all_helpers import create_ws_message, load_model, inference_model
from utils.console import *

from platform import system, version, machine, processor
from socket import gethostname
from psutil import virtual_memory, cpu_count

endpoint = "http://localhost:5000"

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
            "system": system(),
            "version": version(),
            "machine": machine(),
            "processor": processor(),
            "hostname": gethostname(),
            "total_virtual_memory": round(virtual_memory().total / (1024.0 **3), 2),
            "cpu_count": cpu_count()
        }

        NODE_METRICS_DIRECTORY = os.path.join(CONFIG_DIRECTORY, "node_metrics.json")

        # Attempt to update the metrics config
        try:
            print_debug(NODE_METRICS_DIRECTORY)
            with open(NODE_METRICS_DIRECTORY, "w") as f:
                f.write(json.dumps(d, indent = 4))
            print_success("Node metrics file up to date.")
        except Exception as e:
            print_warning(text = f"Node couldnt update metrics config. Directory may not exist.")

    def set_main_config(self, config = None):
        """Sets the :class:`Node`'s config and updates console with debug mode"""
        self.global_config = config

        # Set consoles debug mode
        set_debug_mode(config['dev']['debug_mode'])

    async def listen(self):
        '''Begin listening to the localhost WebSocket'''
        async with websockets.connect("ws://localhost:5001") as ws:
            self.ws = ws
            print_step(f"Node on {gethostname()} started!", justification = "center", style = "green1")
            self.ready = True

            # Let the localhost know this Node is ready
            try:
                requests.post(f"{endpoint}/node-status", data = json.dumps({"status": "active"}), headers = {'Content-Type': 'application/json'})
            except:
                print_error("Could not contact backend to update Node status. This may warrant a complete Node restart.")

            while True:
                res = await ws.recv()
                res = json.loads(res)
                #print_debug(f"{self.node_name}: {res}")
                await self._parse(res) # TODO: Create new process on each parse. Processes will autokill after completion, no need to .join()

    async def inference(self, chat_format, sys_prompt, prompt):
        '''Inferences the LLM with the main prompt that is then to be split up into tasks amongst the :class:`Agent`'s'''
        # Parse and send the prompt to the model to be inferenced
        try:
            model = load_model(os.path.join(MODELS_DIRECTORY, self.global_config['llama_cpp_settings']['node']['filepath']))
            out = inference_model(model, chat_format, sys_prompt, prompt, self.global_config['llama_cpp_settings']['hyperparams'])
            if out is not None:
                out = json.loads(out)
            else:
                print_error(f"{self.node_name} returned None during inference. No output from model was recevied.")

            print_debug(out)

            # Take the output and verify it is in the proper format
            if 'item' in out:
                # Go over each instruction and add it to the Agent Task Queue
                for instruction in out['item']['instruction_set']:
                    self.agent_task_queue.put(instruction['action'])
            else:
                print_error(f"{self.node_name}: Model output not of desired type.\n\n-- Output --\n{out}\n\nCurrent instruction is being negated.")
        except:
            print_error(f"{self.node_name}: An error occurred while loading LLM. Current instruction is being negated.")

    async def _parse(self, msg):
        if msg['target'] == self.node_name or msg['target'] == "any_node":
            if msg['type'] == "function_invoke":
                if msg['data']['function_to_invoke'] == "attach_agent": # Specific bc of the way the parameters are serialized
                    _params = msg['data']['params']
                    await self.attach_agent(uses_inference_endpoint = _params['uses_inference_endpoint'], inference_endpoint = _params['inference_endpoint'], uid = jsonpickle.decode(_params['uid']))
            elif msg['type'] == "new_instruction":
                print_success("This node has been selected for work!")
                # Let localhost know this Node is working
                requests.post(f"{endpoint}/node-status", data = json.dumps({"status": "working"}), headers = {'Content-Type': 'application/json'})
                # Inference the incoming instruction and parse it down into smaller bits to then be added to the Agent Task Queue
                print_error(msg)
                ins = msg['data']['instruction']

                await self.inference(CHAT_ML_PROMPT_FORMAT, SYSTEM_PROMPT_WIN_LINUX_NODE, ins)
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
        print_debug(_recv_agents)
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