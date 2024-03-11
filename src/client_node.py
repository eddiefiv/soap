import asyncio
import time
import websockets
import jsonpickle
import uuid
import argparse

from multiprocessing import Process
from threading import Thread

from node import Node

from utils.helpers.constants import *
from utils.helpers.all_helpers import create_ws_message

from utils.console import *

# Constants
AUTOGEN_DIRECTORY = os.path.join(CONFIG_DIRECTORY, "autogen.json")
print(AUTOGEN_DIRECTORY)

async def main(config):
    # Check to make sure localhost ws is served before proceeding
    print_debug("Starting main loop")
    if not await is_localhost_served():
        print_error("No running localhost websocket. Run localserve.js then try again.")
        quit()
    # Listener
    main_proc = Process(target = sync_localhost, args = (listen_localhost, True), name = "Process-NODE")
    main_proc.start()

    # Keep alive thread
    #ka_thread = Process(target = sync_keep_alive, args = (keep_alive, True), name = "Thread-KeepAlive")
    #ka_thread.start()

    # Main process start node
    await start_node(config)

async def start_node(config):
    node = Node(ntype = NodeType.CLIENT, max_agents = 2)
    node.set_metrics_config()
    node.set_main_config(config)
    await node.listen()
    #agent = Agent(uses_inference_endpoint = True, inference_endpoint = "http://localhost:5001/")

    #node.attach_agent(agent)

    #agent.instruct("Write me a calculator script with addition and subtraction features in python")

async def send_ws(ws, message):
    await ws.send(message)

def sync_localhost(awaitable, new_loop):
    if new_loop:
        loop = asyncio.get_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(listen_localhost())
        loop.close()
    else:
        asyncio.run_coroutine_threadsafe(awaitable(), asyncio.get_running_loop())

def sync_keep_alive(awaitable, new_loop):
    if new_loop:
        loop = asyncio.get_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(keep_alive())
        loop.close()
    else:
        asyncio.run_coroutine_threadsafe(awaitable(), asyncio.get_running_loop())

async def keep_alive():
    print_substep("SYSTEM: Starting Keep Alive thread on ws://localhost:5002", style = "bright_blue")
    async with websockets.connect("ws://localhost:5002") as ws:
        while True:
            await ws.send(create_ws_message(type = "ping", origin = "entry_script", target = "any_agent"))
            _r = await ws.recv()
            #print(_r)
            time.sleep(10)

async def listen_localhost():
    print_substep("SYSTEM: Starting listening process on ws://localhost:5002", style = "bright_blue")
    async with websockets.connect("ws://localhost:5002", ping_timeout = None) as ws:
        await agent_deployer(ws)
        while True:
            # Receive a message from the server
            response = await ws.recv()

            # Parse the received message
            pass

async def agent_deployer(ws): # TODO: Notify the agent when a worker is complete to receive next task. Node-agent-worker flow is success
    '''A temporary ws connection to deploy the initial :class:`Agent`'s and attach them to the node'''
    print_substep("SYSTEM: Starting Agent Deployer", style = "bright_blue")
    msg = create_ws_message(type = "function_invoke", origin = "entry_script", target = "any_node", data = {"function_to_invoke": "attach_agent", "params": {"uses_inference_endpoint": True, "inference_endpoint": "http://localhost:5001", "uid": jsonpickle.encode(uuid.uuid4())}})
    await ws.send(msg)
    #await ws.send(create_ws_message(type = "function_invoke", origin = "entry_script", target = "node", data = {"function_to_invoke": "attach_agent", "params": {"uses_inference_endpoint": True, "inference_endpoint": "http://localhost:5001", "uid": jsonpickle.encode(uuid.uuid4())}}))
    print_substep("SYSTEM: Agent Deployer finished", style = "green1")

async def is_localhost_served():
    try:
        print_debug("Checking for localhost serve status")
        ws = await websockets.connect("ws://localhost:5002")
        await ws.close()
        return True
    except Exception as e:
        print_debug(repr(e))
        return False

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", type = str, default = None, help = "path to a config file.")
    parser.add_argument("--agent_count", type = int, default = None, help = "number of agents to be employed to this machines node. MUST be greater than 0")
    parser.add_argument("--worker_count", type = int, default = None, help = "number of workers to be employed to each agent. MUST be greater than 0")
    parser.add_argument("-d", "--debug", action = "store_true", help = "print debug messages")

    # Parse arguments
    args = parser.parse_args()

    # If a config was supplied
    if args.config is not None:
        if not os.path.exists(args.config):
            print_warning("Invalid config filepath supplied in --config. Resorting to autogen.json saved config if it exists.")

        if os.path.exists(AUTOGEN_DIRECTORY):
            print_debug(f"Overwriting autogen.json with new config: {args.config}")
            with open(AUTOGEN_DIRECTORY, 'w') as f:
                _data = {
                    "last_config_filepath": os.path.abspath(args.config)
                }
                f.write(json.dumps(_data, indent = 4))

    # Try to load autogen.json
    if os.path.isfile(AUTOGEN_DIRECTORY):
        with open(AUTOGEN_DIRECTORY, "r") as f:
            _ = f.read()
            autogen_config = json.loads(_)
        
        try:
            print_info("Found a saved config file in autogen.json, attempting to load...")
            if autogen_config['last_config_filepath'] is not None:
                with open(autogen_config['last_config_filepath'], 'r') as f:
                    config_json = json.loads(f.read())
                print_success(f"Config loaded from {autogen_config['last_config_filepath']}")
        except:
            print_error("A problem occurred while attempting to read the last config filepath from autogen.json. Check the filepath is correct or supply a valid config filepath using --config.")
            quit(1)
    else:
        # No autogen found, --agent_count and --worker_count is required
        print_warning("No autogen.json configuration file found. Creating one automatically. This should only occur during the first run")
        
        # If --config was supplied check for validity, otherwise quit
        if args.config is not None:
            if not os.path.exists(args.config):
                print_error("Valid --config must be supplied during first run.")
                quit(1)
        else:
            print_error("Valid --config must be supplied during first run.")
            quit(1)

        # Write the --config directory to autogen
        with open(AUTOGEN_DIRECTORY, 'w') as f:
            _data = {
                "last_config_filepath": os.path.abspath(args.config)
            }
            f.write(json.dumps(_data, indent = 4))

        print_info(f"Created autogen.json at {AUTOGEN_DIRECTORY}")

        # Load the new config
        with open(args.config, 'r') as f:
            config_json = json.loads(f.read())

    # Update config_json with debug mode
    config_json.update({"dev": {"debug_mode": args.debug}})

    # Update console with debug mode
    set_debug_mode(args.debug)

    # Run listener
    asyncio.get_event_loop().run_until_complete(main(config_json))
    asyncio.get_event_loop().run_forever()