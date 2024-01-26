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

from utils.helpers.constants import WorkerState, WorkerTask
from utils.helpers.worker_helpers import SingleInstruction, MultiInstruction
from utils.helpers.all_helpers import create_ws_message
from utils.console import print_substep, print_step, print_table


class Worker():
    '''The :class:`Worker` holds the code that actually carries out an action given by an :class:`Agent`.
    This could be scraping a website, clicking a button, entering text, taking a screenshot etc.
    A :class:`Worker` is attached to an :class:`Agent` by calling the `.attach_worker()` within the parent :class:`Agent`.
    A :class:`Worker` CAN report back to the :class:`Agent` to perform succeeding tasks. The Worker is the one who give the :class:`Agent` the OK to move on to the next task'''

    def __init__(self, parent_agent, task_queue: Queue, uid):
        self.is_working = False
        self.status: WorkerState = WorkerState.IDLE
        self._parent_agent = parent_agent
        self.worker_uuid = uid.hex
        self.task_queue = task_queue
        self.worker_name = self._parent_agent.agent_name + "_Worker-" + self.worker_uuid
        self.web_driver_path = "webdrivers/chromedriver-win64/chromedriver.exe" if platform.system() == "Windows" else "webdrivers/chromdriver-linux64/chromedriver"

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
        print_step(f"{self.worker_name} with ID {self.worker_uuid} initialized!", style = "green1")
        await self.start_selenium() # Start selenium preemptively
        async with websockets.connect("ws://localhost:5002", ping_timeout = None) as ws:
            self.ws = ws
            print_substep(f"{self.worker_name}: Connected and awaiting task...", style = "green1")
            while True:
                # Wait for task
                self.current_task = self.task_queue.get(block = True, timeout = None)
                # Perform the task NOTE: During task execution, messages will not be received by the client
                await self.give_instructions(self.current_task)
                # Wait for new messages when task is fully complete
                res = await ws.recv() # TODO: Test full messging system, and ensure all communication is success. Still needs messaging system for give agent tasks. Queue system from node to agent.
                res = json.loads(res)
                print(res)

    async def start_selenium(self):
        print_substep(f"{self}: Selenium starting...", style = "bright_blue")
        self.status = WorkerState.STARTING
        # Start selenium in headless ChromeDriver
        self._chrome_options = ChromeOptions()
        self._chrome_options.add_argument("--headless=new")
        self._chrome_options.add_argument("--log-level=3")
        self.web_driver = webdriver.Chrome(options = self._chrome_options)
        # Set back to idle after browser is launched
        self.status = WorkerState.IDLE

    def stop_selenium(self):
        '''Rough close. Selenium will not wait for current action to be done, will just straight up close the WebDriver.'''
        print_substep(f"Selenium stopping on {self}...", style = "bright_blue")
        self.status = WorkerState.STOPPING

        self.web_driver.close()

    async def give_instructions(self, instructions: SingleInstruction):
        if isinstance(instructions, SingleInstruction) or isinstance(instructions, MultiInstruction):
            _i = 1
            for instruction in instructions.get_action_list():
                self.status = WorkerState.TRANSITIONING
                print_substep(f"{self} | Running instruction {_i} of {len(instructions.get_action_list())}...", style = "cyan1")
                print_table(f"{self} Instruction {_i}", items = [[instruction.task.name, instruction.action]], columns = ["Task ID", "Task Action"], color = "blue1")
                await self.do(instruction)
                print_substep(f"{self} | Instruction {_i} of {len(instructions.get_action_list())} complete!", style = "cyan1")
                _i += 1
            await self.report_completion()

    async def report_completion(self):
        '''Reports back to the parent :class:`Agent` to inform it that the task has been completed and it is ready for a new one.'''
        self.is_working = False
        await self.ws.send(create_ws_message(type = "worker_complete", target = self._parent_agent.agent_name, origin = self.worker_name, data = {"result": "success", "task": jsonpickle.encode(self.current_task)}))
        self.current_task = None

    async def do(self, instruction: SingleInstruction):
        _task = instruction.task
        if _task == WorkerTask.GOTO:
            await self.goto(instruction.action)
        elif _task == WorkerTask.SCREENSHOT:
            await self.screenshot_full(self._page, self.worker_uuid)

    async def goto(self, url):
        '''Goes to the specified url and returns a page'''
        self.status = WorkerState.GOING
        self.is_working = True

        # Do the actual going to the specified URL
        self.web_driver.goto(url)

    async def click_browser_selector(self, id, x: int, y: int):
        '''Click somewhere on the browser given a provided selector. Element is located by ID. Make sure the ID is passed properly.'''
        elem = self.web_driver.find_element(value = id)
        elem.click()

    async def screenshot_full(self, filepath):
        '''Takes a screenshot of the full page and returns the bytes result.'''
        self.status = WorkerState.SCREENSHOTTING

        # Take the full screenshot
        _p = self.worker_uuid + ".png"
        self.web_driver.save_screenshot(filename = _p)

    def __str__(self):
        return f"Worker {self.worker_name}"