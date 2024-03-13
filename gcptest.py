import websockets
import asyncio
import json

async def main():
    async with websockets.connect("ws://34.42.227.43:8080") as ws:
        await ws.send(json.dumps({"type": "serverConnect", "origin": "EDDIES_DESKTOP", "target": "GCP soap Server", "msg": {"hostname": "EDDIES_DESKTOP"}}))

        while True:
            res = await ws.recv()
            print(res)

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
    asyncio.get_event_loop().run_forever()