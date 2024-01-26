import json
import jsonpickle
import websockets
import asyncio
import multiprocessing

from multiprocessing import Queue

from agent import Agent

from utils.helpers.constants import NodeType
from utils.helpers.all_helpers import create_ws_message
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
        self.clients = [] # A list of connected WebSocket clients and their respective info
        self.agent_task_queue = Queue()
        self.node_name = f"Node-{gethostname()}"

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

        try:
            with open("../config/node_metrics.json", "w") as f:
                f.write(json.dumps(d, indent = 4))
        except:
            print_warning(text = "Node couldnt update metrics config. Directory may not exist.")

    async def serve_and_listen(self):
        '''Serves a WebSocket server that listens for any and all messages. This is how function calls will be made.
        Only ONE server can be active at a given time, and this is why there can only be one :class:`Node` instance on a single machine.'''
        self.host = "localhost"
        self.port = 5002

        async with websockets.serve(self.ws_main, self.host, self.port) as ws: # Serve the WS
            self.ws = ws
            print_step(f"Node on {gethostname()} started!", justification = "center", style = "green1")
            print_substep(f"NODE: WebSocket served at {self.host} on port {self.port}", style = "bright_blue")
            await asyncio.Future()

    async def inference(self):
        '''Inferences the LLM with the main prompt that is then to be split up into tasks amongst the :class:`Agent`'s'''
        pass

    async def ws_main(self, websocket):
        # Store a copy of the connected client
        self.clients.append(websocket)
        # Handle incoming messages
        try:
            async for message in websocket:
                # Parse incomming message
                print(f"INCOMING MESSAGE: {message}")
                to_all = await self._parse(json.loads(message), websocket)
                print("done parsing")
                if to_all:
                    #Send a response to all connected clients except sender
                    for conn in self.clients:
                        if conn != websocket:
                            await conn.send(message)
        # Handle disconnecting clients
        except websockets.exceptions.ConnectionClosed as e:
            print_warning("A client just disconnected") # TODO: Handle graceful disconnection of agents and workers
        finally:
            self.clients.remove(websocket)

    async def _parse(self, msg, sender):
        if msg['type'] == "heartbeat":
            #print_substep(f"NODE: Heartbeat from {sender}", style = "bright_blue")
            if sender in self.clients:
                print("Found sender in client list.")
        if msg['target'] == "node":
            if msg['type'] == "function_invoke":
                if msg['data']['function_to_invoke'] == "attach_agent": # Specific bc of the way the parameters are serialized
                    _params = msg['data']['params']
                    await self.attach_agent(uses_inference_endpoint = _params['uses_inference_endpoint'], inference_endpoint = _params['inference_endpoint'], uid = jsonpickle.decode(_params['uid']))
            elif msg['type'] == "agent_ready":
                for client in self.clients:
                    await client.send(create_ws_message(type = "agent_dequeue", origin = "node", target = msg['origin'])) # Send dequeue to all clients, targetting send ready agent
            elif msg['type'] == "node_add_queue_item":
                self.agent_task_queue.put(msg['data']['item'])
            return False
        return False

    async def attach_agent(self, uses_inference_endpoint = True, inference_endpoint = "http://localhost:5001", uid = ""):
        '''Attaches an agent to this :class:`Node`. No more agents can be added that exceed the `max_agents` count.'''
        _new_agent = Agent(uses_inference_endpoint = uses_inference_endpoint, inference_endpoint = inference_endpoint, uid = uid, agent_task_queue = self.agent_task_queue)
        if len(self.agents) < self._max_agents: # If there is still room for more agents
            print_substep(f"NODE: Adding Agent: {_new_agent}", style = "bright_blue")
            self.agents.append(_new_agent) # Add agent to a list of agents. List length contains the amount of currently attached agents
            _p = multiprocessing.Process(target = _new_agent.sync_start, name = f"Process-{_new_agent.agent_name}")
            _p.start() # Start the new agent process
        else:
            print_warning("Max agents for this node has already been reached")