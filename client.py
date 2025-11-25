import asyncio
import websockets
import json

WEBSOCKET = None
EVENT_HANDLER = None


def send(action, content=None, sync=True):
    task = WEBSOCKET.send(json.dumps({"action": action, "content": content}))
    if sync:
        asyncio.run(task)
    else:
        asyncio.create_task(task)


# async def send_messages(websocket):
#     while True:
#         user_input = await asyncio.to_thread(input, "请输入要发送的消息: ")
#         send(websocket, "user_input", user_input)
#         # print(f"发送消息: {message}")


async def send_heartbeat():
    while True:
        send("heartbeat", 'ping', sync=False)
        await asyncio.sleep(5)


async def receive_messages():
    while True:
        response = await WEBSOCKET.recv()
        data = json.loads(response)
        action = data.get("action")
        content = data.get("content")
        if action != "heartbeat":
            print(f"Received: {action}")
            EVENT_HANDLER(action, content)


async def communicate(eh):
    global WEBSOCKET, EVENT_HANDLER
    EVENT_HANDLER = eh
    uri = "ws://localhost:8766"
    async with websockets.connect(uri) as websocket:
        print("Connected to the server")
        WEBSOCKET = websocket

        try:
            main = asyncio.gather(send_heartbeat(), receive_messages())
            await main
        except websockets.ConnectionClosed:
            print("Connection to server closed")
            exit(0)


if __name__ == "__main__":
    asyncio.run(communicate(lambda action, content: ...))
