import asyncio
import websockets
import jsonpickle
import json
import platform

from playwright.async_api import async_playwright

from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.action_chains import ActionChains

from multiprocessing import Queue

from utils.helpers.constants import *
from utils.helpers.worker_helpers import SingleInstruction, MultiInstruction
from utils.helpers.all_helpers import create_ws_message, load_config, load_model, inference_model
from utils.console import *

class Worker():
    '''The :class:`Worker` holds the code that actually carries out an action given by an :class:`Agent`.
    This could be scraping a website, clicking a button, entering text, taking a screenshot etc.
    A :class:`Worker` is attached to an :class:`Agent` by calling the `.attach_worker()` within the parent :class:`Agent`.
    A :class:`Worker` CAN report back to the :class:`Agent` to perform succeeding tasks. The Worker is the one who give the :class:`Agent` the OK to move on to the next task'''

    def __init__(self, parent_agent, task_queue: Queue, uid, config):
        self.is_working = False
        self.state: WorkerState = WorkerState.STARTING
        self._parent_agent_name = parent_agent
        self.worker_uuid = uid.hex
        self.task_queue = task_queue
        self.worker_name = self._parent_agent_name + "_Worker-" + self.worker_uuid
        self.web_driver_path = "webdrivers/chromedriver-win64/chromedriver.exe" if platform.system() == "Windows" else "webdrivers/chromdriver-linux64/chromedriver"

        self.global_config = config
        self.worker_config = config['network_configs']['worker']

    def sync_start(self):
        '''Starts the :class:`Worker`. Initially, the worker will run through it's first retrieved task, then listen for websocket messages.
        Only run this method once as it would break this current worker process to have this ran twice.'''
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No running event loop, create new one
            loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.start())
        loop.close()

    async def start(self):
        '''Starts the :class:`Worker`. Initially, the worker will run through it's first retrieved task, then listen for websocket messages.
        Only run this method once as it would break this current worker process to have this ran twice.'''

        # Initialize first
        await self.init()

        async with websockets.connect("ws://localhost:5001", ping_timeout = None) as ws:
            self.ws = ws
            print_substep(f"{self.worker_name}: Connected and awaiting instruction from Agent or External source...", style = "bright_blue")

            # Let parent Agent know this Worker is ready for tasks
            self.state = WorkerState.READY
            await ws.send(create_ws_message(type = "worker_ready", origin = self.worker_name, target = self._parent_agent_name))
            while True:
                # Wait for new messages when task is fully complete
                res = await ws.recv() # TODO: Test full messging system, and ensure all communication is success. Still needs messaging system for give agent tasks. Queue system from node to agent.
                print_debug(res)
                res = json.loads(res)
                await self._parse(res)

    async def init(self):
        '''Does any pre-ready initializing tasks'''

        # Start selenium preemptively
        await self.start_selenium()

        print_success(f"{self.worker_name} with ID {self.worker_uuid} initialized!")

    async def start_selenium(self):
        print_substep(f"{self}: Selenium starting...", style = "bright_blue")
        self.state = WorkerState.STARTING
        # Start selenium in headless ChromeDriver
        self._chrome_options = ChromeOptions()
        self._chrome_options.add_argument("--headless=new")
        self._chrome_options.add_argument("--log-level=3")
        self.web_driver = webdriver.Chrome(options = self._chrome_options)
        # Set back to idle after browser is launched
        self.state = WorkerState.IDLE

    def stop_selenium(self):
        '''Rough close. Selenium will not wait for current action to be done, will just straight up close the WebDriver.'''
        print_substep(f"Selenium stopping on {self}...", style = "bright_blue")
        self.state = WorkerState.STOPPING

        self.web_driver.close()

    async def give_instructions(self, instructions):
        '''Take an instruction set and proceed with it'''
        _i = 1
        for instruction in instructions:
            self.state = WorkerState.TRANSITIONING
            print_substep(f"{self} | Running instruction {_i} of {len(instructions)}...", style = "cyan1")
            print_table(f"{self} Instruction {_i}", items = [[instruction['operation'], instruction['action']]], columns = ["Task ID", "Task Action"], color = "blue1")
            await self.do(instruction)
            print_substep(f"{self} | Instruction {_i} of {len(instructions)} complete!", style = "cyan1")
            _i += 1
        await self.report_completion()

    async def report_completion(self):
        '''Reports back to the parent :class:`Agent` to inform it that the task has been completed and it is ready for a new one.'''
        self.state = WorkerState.IDLE
        self.is_working = False
        await self.ws.send(create_ws_message(type = "worker_complete", target = self._parent_agent_name, origin = self.worker_name, data = {"result": "success", "task": {"instruction_type": "multi", "instruction_set": [(instruction.out()[0].value, instruction.out()[1]) for instruction in self.current_task._instructions]}}))
        self.current_task = None

    async def update_state(self, new_state: WorkerState):
        self.state = new_state

        await self.ws.send(create_ws_message(type = "worker_update", origin = self.worker_name, target = self._parent_agent_name, data = {"new_state": new_state.value})) # TODO

    async def _parse(self, msg):
        if msg['target'] == self.worker_name or msg['target'] == "any":
            if msg['type'] == "update_config":
                # Attempt to load the config
                cfg = load_config()

                if cfg is not False:
                    self.global_config = cfg
                    self.worker_config = cfg['network_configs']
                    print_success(f"{self.worker_name} successfully hot-loaded new config")
            if msg['type'] == "worker_dequeue":
                await self.dequeue()

    async def dequeue(self):
        '''Grabs the first task from the Worker Task Queue and begins to run the tasks sequentially.'''
        print_info(f"{self.worker_name}: Awaiting task from Worker Task Queue...")
        while not self.task_queue.empty():
            self.current_task = self.task_queue.get(block = True, timeout = 5)

            if self.current_task is not None:
                print_success(f"{self.worker_name}: Found and executing task {self.current_task} from Worker Task Queue")

                # Perform the task NOTE: During task execution, messages will not be received by this client
                await self.give_instructions(self.current_task)
            else:
                print_warning(f"{self.worker_name}: Worker Task Queue empty, returning to IDLE")
                self.state = WorkerState.IDLE

                # Let parenting Agent know
                await self.ws.send(create_ws_message(type = "worker_complete", origin = self.worker_name, target = self.agent))

    async def do(self, instruction):
        #_task = instruction.task.value
        operation = instruction['operation']
        action = instruction['action']
        print_debug(instruction)
        if operation == "goto":
            await self.goto(action)
        elif operation == "screenshot":
            await self.screenshot_full(self.worker_uuid)
        elif operation == "write":
            await self.write_to_file(action['content'], action['filename'] + action['extension'])
        elif operation == "generate_code":
            await self.inference_code_description(action['content'], action['filename'] + action['extension'])
        else:
            print_error(f"Invalid WorkerTask type: {instruction}")

    # ---- INSTRUCTIONS ----

    async def goto(self, url):
        '''Goes to the specified url and returns a page'''
        self.state = WorkerState.GOING
        self.is_working = True

        # Do the actual going to the specified URL
        self.web_driver.get(url)

    async def click_browser_selector(self, id, x: int, y: int):
        '''Click somewhere on the browser given a provided selector. Element is located by ID. Make sure the ID is passed properly.'''
        elem = self.web_driver.find_element(value = id)
        elem.click()

    async def screenshot_full(self, filepath):
        '''Takes a screenshot of the full page and returns the bytes result.'''
        self.state = WorkerState.SCREENSHOTTING

        # Take the full screenshot
        try:
            _p = self.worker_uuid + ".png"
            self.web_driver.save_screenshot(filename = _p)
        except Exception as e:
            print_error("Failed to ss" + e)

    async def write_to_file(self, filepath, content):
        '''Writes content to a file

        Params:
            filepath: the filepath of the file to be written
            content: what to go in the file
        '''
        with open(os.path.join(NETWORK_GEN, filepath), 'w') as f:
            f.write(content)

    async def inference_code_description(self, description, filename):
        '''Generates code using a finetuned code model given the code description and writes it to a file

        Params
            description: the description of the code to be generated
            filename: the file to save the code in the network_gen directory
        '''

        model = load_model(
            os.path.join(MODELS_DIRECTORY, self.worker_config['finetuned']['code_model_filepath']),
            self.worker_config['gpu_layer_count'],
            self.worker_config['ctx_size'],
            self.worker_config['batch_size'],
            verbose = True)
        out = inference_model(
            model = model,
            chat_format = chat_format_from_id(self.worker_config['chat_format']['id']),
            system_message = SYSTEM_PROMPT_WIN_LINUX_FINETUNED_CODE,
            user_message = description,
            hyperparams = self.global_config['network_configs']['hyperparams'])

        if out is not None:
            if type(out) == str:
                out = json.loads(out)
        else:
            print_error(f"{self.worker_name} returned None during inference. No output from model was received.")
            return

        with open(os.path.join(NETWORK_GEN, filename), 'w') as f:
            f.write(out)

    def __str__(self):
        return f"Worker {self.worker_name}"