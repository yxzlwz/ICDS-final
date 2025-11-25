import asyncio
import websockets
import json
from time import time
from pathlib import Path

from sonnets import data as sonnets_data
GAME_ID_COUNTER = 0
path = Path(__file__).parent.resolve()
name2websocket = {}
pending_game_invites = {}
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
    elif action == 'invite_game':
        target_username = content.get('target_user')
        if target_username not in name2websocket:
            send_response(websocket, {
                "action": 'system_message',
                "content": f"User {target_username} is not online."
            })
            return
        target_ws = name2websocket[target_username]
        pending_game_invites[target_username] = username
        send_response(target_ws, {
            "action": "game_invited",
            "content": {
                "inviter": websocket.username
            }
        })
        send_response(websocket, {
            "action": "system_message",
            "content": f"Game invitation sent to {target_username}."
        })
        return
    elif action == 'game_response':
        inviter = content.get('target_user')
        response = content.get('response')
        if inviter not in pending_game_invites or pending_game_invites[inviter] != username:
            send_response(websocket, {
                "action": 'system_message',
                "content": f"No pending game invitation from {inviter}."
            })
            return
        inviter_websocket = name2websocket.get(inviter)
        if response == 'accepted':
            global GAME_ID_COUNTER
            current_game_id = GAME_ID_COUNTER
            GAME_ID_COUNTER += 1
            if inviter_websocket:
                send_response(inviter_websocket, {
                    "action": "game_start",
                    "content": {'player_id': 0,
                                'opponent': username,
                                'game_id': current_game_id 
                                }
                })
                send_response(inviter_websocket, {
                    "action": "system_message",
                    "content": f"{username} accepted your game invitation. Game ID: {current_game_id}"
                })
            send_response(websocket, {
                "action": "game_start", 
                "content": {'player_id': 1, 'opponent': inviter,'game_id': current_game_id} 
            })
            send_response(websocket, {
                "action": "system_message",
                "content": f"You accepted the game invitation from {inviter}. Game ID: {current_game_id}"
            })
            del pending_game_invites[username]
            return 
        elif response == 'rejected': 
            if inviter_websocket: 
                send_response(inviter_websocket, {
                    "action": "system_message",
                    "content": f"{username} rejected your game invitation."
                })
            send_response(websocket, {
                "action": "system_message",
                "content": f"You rejected the game invitation from {inviter}."
            })
        del pending_game_invites[username] 
        return 
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
