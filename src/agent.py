import requests
import json
import asyncio
import uuid
import websockets
import jsonpickle
import multiprocessing
import time

from urllib import parse

from multiprocessing import Queue
# from queue import Queue

from utils.helpers.agent_helpers import get_inference_config, validate_endpoint
from utils.helpers.worker_helpers import *
from utils.helpers.all_helpers import create_ws_message, load_model, inference_model, load_config
from utils.helpers.constants import *

from utils.console import *

from worker import Worker

class Agent():
    '''An :class:`Agent` employs :class:`Worker`'s that carry out their given task.
    Typically, the :class:`Agent` is where the inferencing takes place and the
    worker is the scripting that carries out the action generated by the :class:`Agent` response.
    An :class:`Agent` must be attached to a Node in order to receive instruction, this can be done
    by calling `.attach_agent()` on the parent :class:`Node`.'''

    def __init__(self, global_config, parent_node_name, uses_inference_endpoint = True, inference_endpoint = "http://localhost:5001", uid = "", agent_task_queue: Queue = None) -> None:
        self._uses_inference_endpoint = uses_inference_endpoint
        self._inference_endpoint = inference_endpoint
        self._inference_config = get_inference_config()
        self.is_valid = validate_endpoint(inference_endpoint) # Is the endpoint a valid and reachable endpoint. If false, the endpoint may be incorrectly written or not open

        # Set the global config sent from the node
        self.global_config = global_config
        self.agent_config = global_config['network_configs']['agent']

        # Update consoles debug mode
        set_debug_mode(global_config['dev']['debug_mode'])

        self._parent_node_name = parent_node_name

        self.agent_id = uid.hex if uid != "" else uuid.uuid4().hex
        self.agent_name = f"Agent-{self.agent_id}"

        self.agent_task_queue = agent_task_queue
        self.task_queue = Queue()

        # A list of workers in this Agent's Fleet
        self._workers = []

        # Whether to continue dequeuing after a single dequeue or not
        self.persist_dequeue = True

    async def start(self):
        '''Starts the :class:`Agent` and beings listening for instruction on the localhost server.
        Wont be able to send messages to the websocket server without having received a message first that prompts a sent message.
        Must be ran in order to give tasks to :class:`Worker`'s'''
        async with websockets.connect("ws://localhost:5001") as ws:
            self.ws = ws
            #hb = threading.Thread(target = self.sync_heartbeat, args = (ws, 2)) # Start the heartbeating thread to keep this connection alive
            #hb.start()

            # Load configs before informing node of readyness
            _successfully_connected_workers = await self.init()

            print_substep(f"{self.agent_name}: Ready to receive instruction from Node!", style = "green1")

            # Wait until all workers are ready and idle to proceed
            while len(self._workers) != len(self.get_ready_workers()):
                res = await ws.recv()
                res = json.loads(res)
                if res['target'] == self.agent_name and res['type'] == "worker_ready":
                    for i in range(len(self._workers)):
                        print_debug(self._workers[i])
                        if self._workers[i]['name'] == res['origin']:
                            self._workers[i]['state'] = WorkerState.READY.value
                            print_debug(self._workers)

            # Let all workers begin dequeue
            for worker in self._workers:
                worker['state'] = WorkerState.IDLE.value
                await ws.send(create_ws_message(type = "worker_dequeue", origin = self.agent_name, target = worker['name']))

            # Ready this Agent and let the Node know
            await ws.send(create_ws_message(type = "agent_ready", origin = self.agent_name, target = self._parent_node_name))

            while True:
                try:
                    #print_debug("Listening...")
                    res = await ws.recv()
                    res = json.loads(res)
                    #print_debug(res)
                    assert type(res) == dict, print_error("Received message is not of type 'dict'")

                    # Maybe create a new thread to parse and run workers if the websocket keeps cutting out during task awaiting
                    await self._parse(res)
                except Exception as e:
                    print_error(f"Problem occurred during parsing {type(e)}:\n\n{repr(e)}")
                    #self.start # Try to notify Node somehow for a more graceful shutdown

    async def init(self) -> int:
        '''Attaches :class:`Workers` and sets up any other pre-ready configurations'''
        _num_max_workers = self.global_config['general']['worker_count']
        _num_success = 0

        print_info(f"{self.agent_name}: Beginning creating and attaching Workers...")

        for _ in range(_num_max_workers):
            try:
                print_info(f"{self.agent_name}: Creating and attaching Worker {_} of {_num_max_workers}")
                await self._employ_worker(self.agent_name, self.task_queue, uuid.uuid4())
                _num_success += 1
            except Exception as e:
                print_error(f"{self.agent_name}: Worker creation and attachment failed. Skipping.\n\n{repr(e)}")

        print_success(f"{self.agent_name}: Successfully created and attached {_num_success} of {_num_max_workers} Workers!")

    def sync_start(self):
        '''Starts the :class:`Agent` and beings listening for instruction on the localhost server.
        Wont be able to send messages to the websocket server without having received a message first that prompts a sent message.
        Must be ran in order to give tasks to :class:`Workers`'''
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.start())
        loop.close()

    def sync_heartbeat(self, ws, interval):
        '''Run a heartbeat to keep the WebSocket client alive while working on a task or parsing a new message.
        The heartbeat will run on :class:`Agent` creation, and ends when the :class:`Agent` is destroyed.'''
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.heartbeat(ws, interval))
        loop.close()

    async def heartbeat(self, ws, interval):
        '''Run a heartbeat to keep the WebSocket client alive while working on a task or parsing a new message.
        The heartbeat will run on :class:`Agent` creation, and ends when the :class:`Agent` is destroyed.'''
        while True:
            print_substep(f"{self.agent_name}: Sending heartbeat.", style = "bright_blue")
            try:
                await ws.send(create_ws_message(type = "heartbeat", origin = self.agent_name, target = self._parent_node_name, data = {}))
            except Exception as e:
                print_error(f"Couldnt send heartbeat. Trying again.\n\n{repr(e)}")
            time.sleep(interval)

    async def dequeue(self):
        '''Grabs the first task from the Agent Task Queue and inferences to split it up into smaller tasks for the :class:`Workers`.
        NOTE: :class:`Agent` will NOT receive messages from the localhost during this time. Only when the task has been inferenced and put into
        the Task Queue will it listen again.'''
        print_info(f"{self.agent_name}: Beginning scanning for tasks in Agent Task Queue...")
        # Wait to get a task from Node
        try:
            task = self.agent_task_queue.get(block = True, timeout = None)

            print_success(f"{self.agent_name}: Agent found task: {task}")

            # Begin the prompting to parse task further
            await self.instruct(task, task)

            # Let parenting Node know an item has been pulled and dealt with
            await self.ws.send(create_ws_message(type = "agent_dequeue_success", origin = self.agent_name, target = self._parent_node_name))
        except Exception as e:
            print_error(f"Agent Task Queue empty. Didnt retrieve any data.\n\n{repr(e)}")

    def get_idle_workers(self):
        _idle_workers = []

        for worker in self._workers:
            if worker["state"] == WorkerState.IDLE.value:
                _idle_workers.append(worker)
        return _idle_workers

    def get_ready_workers(self):
        _idle_workers = []

        for worker in self._workers:
            if worker["state"] == WorkerState.READY.value:
                _idle_workers.append(worker)
        #print_debug(_idle_workers)
        return _idle_workers

    async def flush_agent(self):
        '''Essentially reset the :class:`Agent` after all tasks given are completed. This usually includes after the Agent Task Queue is empty as well.
        Resets: Agent State, '''
        pass

    async def _parse(self, msg):
        if msg['target'] == self.agent_name or msg['target'] == "any_agent" or msg['target'] == "any":
            if msg['type'] == "update_config":
                # Attempt to load the config
                cfg = load_config()

                if cfg is not False:
                    self.global_config = cfg
                    self.agent_config = cfg['network_configs']['agent']
                    print_success(f"{self.agent_name} successfully hot-loaded new config")
            if msg['type'] == "function_invoke":
                if msg['data']['function_to_invoke'] == "instruct":
                    self.instruct(prompt = msg['data']['params']['prompt'])
                elif msg['data']['function_to_invoke'] == "_put_queue":
                    _deserialized_item = jsonpickle.decode(msg['data']['params']['item'])
                    self._put_queue(item = _deserialized_item)
            elif msg['type'] == "worker_update":
                for i in range(len(self._workers)):
                    if self._workers[i]['name'] == msg['origin']:
                        self._workers[i]['state'] == msg['data']['new_state']
            elif msg['type'] == "worker_ready":
                _idx = self.find_worker_idx_from_name(msg['origin'])

                if _idx is not None:
                    self._workers[_idx]['state'] == WorkerState.DEQUEUE.value
                await self.ws.send(create_ws_message(type = "worker_dequeue", origin = self.agent_name, target = msg['origin']))
            elif msg['type'] == "worker_complete":
                _idx = self.find_worker_idx_from_name(msg['origin'])

                # Re-dequeue the worker on it's completion if the Worker Task Queue isn't empty. Based on global configs, this may not be the case and the worker may be terminated.
                print_success(f"{self.agent_name}: {msg['origin']} completed their task: {msg['data']['result']}. Worker is now open for pulling from Worker Task Queue again.")

                # If the queue isn't empty, keep dequeing idle workers, otherwise check to see if all workers are finished and if so, then inform the parenting node and await further instruction
                if not self.task_queue.empty():
                    if _idx is not None:
                        self._workers[_idx]['state'] == WorkerState.DEQUEUE.value
                    await self.ws.send(create_ws_message(type = "worker_dequeue", origin = self.agent_name, target = msg['origin']))
                else:
                    if _idx is not None:
                        self._workers[_idx]['state'] == WorkerState.IDLE.value
                    if len(self._workers) == len(self.get_idle_workers()): # If the number of idle workers is the same as the number of attached workers
                        await self.ws.send(create_ws_message(type = "agent_complete", origin = self.agent_name, target = self._parent_node_name))
            elif msg['type'] == "agent_dequeue":
                # Dequeue agent then let Node know when finished for further instruction
                await self.dequeue()
            elif msg['type'] == "ping":
                print_substep(f"{self.agent_name}: Received ping from {msg['origin']}", style = "bright_blue")
                return True # Maybe send a pong back to the Node. If need be

    def find_worker_idx_from_name(self, name):
        '''Tries to find an entry in self.agents matching the given name. Returns None if nothing is found'''
        for i in range(len(self._workers)):
            if self._workers[i]['name'] == name:
                return i
        return None

    def _put_queue(self, item):
        '''Put an item into the Task Queue. Active :class:`Worker`'s will automatically get items out of the Task Queue and run them as they're available.
        Example item: `MultiInstruction([SingleInstruction(WorkerTask.GOTO, "https://google.com"), SingleInstruction(WorkerTask.SCREENSHOT, None)])`'''
        try:
            self.task_queue.put(item, block = False)
        except Exception as e:
            print_error(text = f"Insertting {item} into Task Queue, failed. It is possible the queue was full, or something else happened. Task aborted.\n\n{repr(e)}")

    async def instruct(self, prompt: str, task):
        '''Passes on the prompt to the model associated with this :class:`Agent` and waits for a response.
        Don't run this outside of a :class:`Node` just to ensure that no arbitrary inferences get prompted causing potential confusion in the LLM.'''

        #assert self.is_valid, "No valid endpoint provided, please update the endpoint using .update_endpoint() and then .reload_agent()"

        # Inference model and split up the selected task from node into smaller pieces for workers
        model = load_model(
            os.path.join(MODELS_DIRECTORY, self.global_config['network_configs']['agent']['filepath']),
            self.agent_config['gpu_layer_count'],
            self.agent_config['ctx_size'],
            self.agent_config['batch_size'],
            verbose = True)
        out = inference_model(
            model = model,
            chat_format = chat_format_from_id(self.agent_config['chat_format']['id']),
            system_message = SYSTEM_PROMPT_WIN_LINUX_AGENT,
            user_message = prompt,
            hyperparams = self.global_config['network_configs']['hyperparams']
        )
        if out is not None:
            if type(out) == str:
                out = json.loads(out)
        else:
            print_error(f"{self.agent_name} returned None during inference. No output from model was received.")

        # Reconstruct the instruction after inferencing
        instructions = out['item']['instruction_set']
        #task = reconstruct_multi_instruction(task)
        for instruction in instructions:
            self.task_queue.put([instruction])

        # Unidle all workers that were previously idle
        for worker in self.get_idle_workers():
            await self.ws.send(create_ws_message(type = "worker_dequeue", origin = self.agent_name, target = worker['name']))

    def update_endpoint(self, new_endpoint: str):
        '''Updates the :class:`Agent`'s endpoint with a new one
        `.refresh_agent()` must be called after setting a new endpoint in order to use the new endpoint'''

        self._inference_endpoint = new_endpoint

    def refresh_agent(self):
        '''Runs validity checks and updates configurations again to ensure the :class:`Agent` is up to date
        Typically only ran after updating something like the endpoint after :class:`Agent` initialization'''

        self.is_valid = validate_endpoint(self._inference_endpoint)

    def on_worker_complete(self, worker: Worker):
        '''Should only be called as a callback function when a :class:`Worker` is complete with their given task'''
        if worker not in self._workers: # If the worker the call was from is not an attached worker
            print("Task completion callback received from unknown Worker. Ignoring completion call.")
        else:
            print(f"Worker: {worker.worker_uuid} completed their task.")

    async def _employ_worker(self, parent_agent, task_queue, uuid):
        '''Initializes a new :class:`Worker` and attaches them to this object'''
        print_substep(f"{self.agent_name}: Employing new Worker with UUID: {uuid}", style = "bright_blue")

        worker = Worker(parent_agent = parent_agent, task_queue = task_queue, uid = uuid, config = self.global_config)
        self._workers.append({"name": worker.worker_name, "state": WorkerState.IDLE.value})

        _p = multiprocessing.Process(target = worker.sync_start, name = f"Thread-{worker.worker_name}")
        _p.start() # Start the new worker process

    def test(self):
        print("Test process")

    def _gen_body(self, prompt: str):
        if self._inference_config != None:
            _new_config = self._inference_config
            _new_config.update({"prompt:": prompt})

            return _new_config
        else:
            return {"prompt": prompt}

    def _request(self, method: HTTPMethod, path: str, body = None):
        try:
            if type(body) == dict:
                if body != None:
                    _body = json.dumps(body)
                else:
                    _body = None
            elif type(body) == str:
                _body = body
            else:
                raise RuntimeError("(_post) body was not given a valid json string or dict or None")

            if method == HTTPMethod.POST:
                self._post(path, body)
            elif method == HTTPMethod.GET:
                self._get(path, body)
        except Exception as e:
            print_warning(e)

            return False, None

    def _post(self, path: str, body = None):
        _r = True, requests.post(parse.urljoin(self._inference_endpoint, path), data = body)

        return _r

    def _get(self, path: str, body = None):
        _r = True, requests.get(parse.urljoin(self._inference_endpoint, path), data = body)

        return _r

    def __str__(self):
        return self.agent_name