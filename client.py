import asyncio
import websockets
import json

WEBSOCKET = None
EVENT_HANDLER = None
EVENT_LOOP = None


def send(action, content=None, sync=True):
    global EVENT_LOOP
    if WEBSOCKET is None:
        print('[Client Error] Cannot send message: WEBSOCKET is not yet connected.')
        return
    coro = WEBSOCKET.send(json.dumps({'action': action, 'content': content}))
    if sync:
        if EVENT_LOOP is not None and EVENT_LOOP.is_running():
            try:
                future = asyncio.run_coroutine_threadsafe(coro, EVENT_LOOP)
                future.result(timeout=5)
            except Exception as e:
                print(f'[Client] Error sending message synchronously (threadsafe): {e}')
        else:
            try:
                asyncio.run(coro)
            except Exception as e:
                print(f'[Client] Error sending message synchronously (blocking run): {e}')
    else:
        if EVENT_LOOP is not None and EVENT_LOOP.is_running():
            asyncio.create_task(coro)
        else:
            print('[Client Error] Cannot create async task: Event loop is not running.')


# async def send_messages(websocket):
#     while True:
#         user_input = await asyncio.to_thread(input, "请输入要发送的消息: ")
#         send(websocket, "user_input", user_input)
#         # print(f"发送消息: {message}")


async def send_heartbeat():
    while True:
        send('heartbeat', 'ping', sync=False)
        await asyncio.sleep(5)


async def receive_messages():
    while True:
        try:
            if WEBSOCKET is None:
                await asyncio.sleep(0.1)
                continue
            response = await WEBSOCKET.recv()
            data = json.loads(response)
            action = data.get('action')
            content = data.get('content')

            if action != 'heartbeat':
                print(f'Received: {action}')
                EVENT_HANDLER(action, content)
        except Exception as e:
            if not isinstance(e, websockets.ConnectionClosedOK):
                print(f'[Client] Error receiving message: {e}')
            break


async def communicate(eh):
    global WEBSOCKET, EVENT_HANDLER, EVENT_LOOP
    EVENT_HANDLER = eh
    EVENT_LOOP = asyncio.get_running_loop()
    uri = 'ws://localhost:8766'
    async with websockets.connect(uri) as websocket:
        print('Connected to the server')
        WEBSOCKET = websocket

        try:
            main = asyncio.gather(send_heartbeat(), receive_messages())
            await main
        except websockets.ConnectionClosed:
            print('Connection to server closed')
            exit(0)


if __name__ == '__main__':
    asyncio.run(communicate(lambda action, content: ...))
