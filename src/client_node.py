import asyncio
import time
import websockets
import jsonpickle
import uuid

from multiprocessing import Process
from threading import Thread

from node import Node

from utils.helpers.constants import NodeType
from utils.helpers.all_helpers import create_ws_message

from utils.console import *

async def main():
    # Check to make sure localhost ws is served before proceeding
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
    await start_node()

async def start_node():
    node = Node(ntype = NodeType.CLIENT, max_agents = 2)
    node.set_metrics_config()
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
    time.sleep(2) # Allow time for WebSocket to spin up
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
    time.sleep(2) # Allow time for WebSocket to spin up
    await ws.send(create_ws_message(type = "function_invoke", origin = "entry_script", target = "node", data = {"function_to_invoke": "attach_agent", "params": {"uses_inference_endpoint": True, "inference_endpoint": "http://localhost:5001", "uid": jsonpickle.encode(uuid.uuid4())}}))
    #await ws.send(create_ws_message(type = "function_invoke", origin = "entry_script", target = "node", data = {"function_to_invoke": "attach_agent", "params": {"uses_inference_endpoint": True, "inference_endpoint": "http://localhost:5001", "uid": jsonpickle.encode(uuid.uuid4())}}))
    print_substep("SYSTEM: Agent Deployer finished", style = "green1")

async def is_localhost_served():
    try:
        ws = await websockets.connect("ws://localhost:5002")
        await ws.close()
        return True
    except Exception as e:
        print(e)
        return False

if __name__ == "__main__":
    # Run listener
    asyncio.get_event_loop().run_until_complete(main())
    asyncio.get_event_loop().run_forever()