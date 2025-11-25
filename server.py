import asyncio
import websockets
import json
from time import time
from pathlib import Path

from sonnets import data as sonnets_data

path = Path(__file__).parent.resolve()
name2websocket = {}

rooms = {}
NUM = 0
example_rooms = {
    'num': {
        'members': ['user1', 'user2'],
        'uuid': 'md5',
        'group': True,
        'owner': 'user1',
        'history': [
            {
                'user': 'user1',
                'message': 'Hello!'
            },
        ],
    }
}


def save():
    with open(path / 'rooms.json', 'w', encoding='utf-8') as f:
        json.dump(rooms, f, indent=2, ensure_ascii=False)


def send_response(websocket, response):
    asyncio.create_task(websocket.send(json.dumps(response)))


def send_my_room_list(websocket, username):
    my_rooms = []
    for i, j in rooms.items():
        if username in j['members']:
            my_rooms.append(f"[{i}] {', '.join(j['members'])}")
    send_response(websocket, {"action": 'my_room_list', "content": my_rooms})


async def action_handler(websocket, data):
    global NUM
    action = data.get("action")
    content = data.get("content")
    username = getattr(websocket, 'username', None)
    if action == "heartbeat":
        send_response(websocket, {"action": "heartbeat", "content": "pong"})
        return
    print(f"Received: {data}")
    if action == "sonnet":
        if type(content) != int or not (1 <= content <= len(sonnets_data)):
            send_response(websocket, {
                "action": 'system',
                "content": "Invalid sonnet ID."
            })
        else:
            send_response(websocket, {
                "action": 'system',
                "content": sonnets_data[content]
            })
    elif action == "login":
        setattr(websocket, 'username', content)
        name2websocket[content] = websocket
        send_response(websocket, {"action": 'login', "content": None})
    elif action == 'user_list':
        targets = []
        for i in name2websocket.keys():
            targets.append(i)
        send_response(websocket, {"action": 'user_list', "content": targets})
    elif action == 'my_room_list':
        send_my_room_list(websocket, username)
    elif action == 'create_room':
        num = NUM
        NUM += 1
        members: list = list(set(content + [username]))
        members.sort()
        uuid = '|'.join(members)
        for i, j in rooms.items():
            if j.get('uuid', None) == uuid:
                send_response(websocket, {
                    "action": 'switch_room',
                    "content": i
                })
                return
        room = {
            'uuid': uuid,
            'members': members,
            'group': len(members) > 2,
            'owner': username,
            'history': [],
        }
        rooms[str(num)] = room
        send_my_room_list(websocket, username)
        await asyncio.sleep(0.5)
        send_response(websocket, {
            "action": 'switch_room',
            "content": str(num)
        })
    elif action == 'send_message':
        room_id = content.get('room_id')
        message = content.get('message')
        if room_id not in rooms:
            send_response(websocket, {
                "action": 'system',
                "content": "Room does not exist."
            })
            return
        room = rooms[room_id]
        if username not in room['members']:
            send_response(
                websocket, {
                    "action": 'system',
                    "content": "You are not a member of this room."
                })
            return
        room['history'].append({
            'user': username,
            'message': message,
            'time': round(time(), 3)
        })
        for member in room['members']:
            if member in name2websocket:
                send_response(
                    name2websocket[member], {
                        "action": 'new_message',
                        "content": {
                            'room_id': room_id,
                            **room['history'][-1]
                        }
                    })
    elif action == 'history':
        room_id = content
        if room_id not in rooms:
            send_response(websocket, {
                "action": 'system',
                "content": "Room does not exist."
            })
            return
        room = rooms[room_id]
        if username not in room['members']:
            send_response(
                websocket, {
                    "action": 'system',
                    "content": "You are not a member of this room."
                })
            return
        send_response(
            websocket, {
                "action": 'history',
                "content": {
                    'room_id': room_id,
                    'history': room['history'][-100:]
                }
            })
    else:
        print(f"Unknown action: {action}")


async def handle_connection(websocket):
    print("Client connected")
    try:
        async for message in websocket:
            data = json.loads(message)
            await action_handler(websocket, data)
            # send_response(websocket, {"status": "ok", "received": data})
    except websockets.ConnectionClosed:
        username = getattr(websocket, 'username', None)
        if username and username in name2websocket:
            del name2websocket[username]
        print("Client disconnected")


async def periodic_save():
    while True:
        save()
        await asyncio.sleep(5)


async def main():
    asyncio.create_task(periodic_save())
    server = await websockets.serve(handle_connection, "localhost", 8766)
    print("WebSocket started, listening localhost:8766")
    await server.wait_closed()


if __name__ == "__main__":
    if (path / 'rooms.json').exists():
        with open(path / 'rooms.json', 'r', encoding='utf-8') as f:
            rooms = json.load(f)
    for i in rooms.keys():
        if int(i) > NUM:
            NUM = int(i)
    asyncio.run(main())
