import asyncio
import websockets
import json
from time import time
from pathlib import Path
import re
from collections import Counter
from chatbot import get_response
from sonnets import data as sonnets_data
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

s_ana = SentimentIntensityAnalyzer()
GAME_ID_COUNTER = 0
path = Path(__file__).parent.resolve()
name2websocket = {}
name2botpersonality = {}
pending_game_invites = {}
rooms = {}

NUM = 0


def save():
    with open(path / 'rooms.json', 'w', encoding='utf-8') as f:
        json.dump(rooms, f, indent=2, ensure_ascii=False)


def send_response(websocket, response):
    asyncio.create_task(websocket.send(json.dumps(response)))


def do_s_ana(message):
    res = s_ana.polarity_scores(message)
    neg = res['neg']
    neu = res['neu']
    pos = res['pos']
    if max(neg, neu, pos) == pos:
        return 'positive'
    elif max(neg, neu, pos) == neu:
        return 'neutral'
    else:
        return 'negative'


def send_my_room_list(websocket, username):
    my_rooms = []
    for i, j in rooms.items():
        if username in j['members']:
            my_rooms.append(f'[{i}] {", ".join(j["members"])}')
    send_response(websocket, {'action': 'my_room_list', 'content': my_rooms})


async def bot_response(websocket, history, room_id, username):
    history = [{'user': i['user'], 'message': i['message']} for i in history[-10:]]
    response = get_response(
        [
            {
                'role': 'system',
                'content': 'In your answer, no markdown formatting is needed. No reasoning.'
                "Answer as short as possible. Don't quote chat history."
                f'Reply in {name2botpersonality[username]} tone.'
                if username in name2botpersonality
                else '',
            },
            {'role': 'user', 'content': 'Chat history: ' + json.dumps(history[:-1], ensure_ascii=False)},
            {'role': 'user', 'content': history[-1]['message']},
        ]
    )
    await action_handler(
        websocket,
        {'action': 'bot_response', 'content': {'room_id': room_id, 'response': f'@{username} {response}'}},
    )


async def action_handler(websocket, data):
    global NUM
    action = data.get('action')
    content = data.get('content')
    username = getattr(websocket, 'username', None)
    if action == 'heartbeat':
        send_response(websocket, {'action': 'heartbeat', 'content': 'pong'})
        return
    print(f'Received: {data}')
    if action == 'sonnet':
        if type(content) is not int or not (1 <= content <= len(sonnets_data)):
            send_response(websocket, {'action': 'system', 'content': 'Invalid sonnet ID.'})
        else:
            send_response(websocket, {'action': 'system', 'content': sonnets_data[content]})
    elif action == 'login':
        setattr(websocket, 'username', content)
        name2websocket[content] = websocket
        send_response(websocket, {'action': 'login', 'content': None})
    elif action == 'user_list':
        targets = []
        for i in name2websocket.keys():
            targets.append(i)
        send_response(websocket, {'action': 'user_list', 'content': targets})
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
                send_response(websocket, {'action': 'switch_room', 'content': i})
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
        send_response(websocket, {'action': 'switch_room', 'content': str(num)})

    elif action == 'send_message':
        room_id = content.get('room_id')
        message = content.get('message')
        if room_id not in rooms:
            send_response(websocket, {'action': 'system', 'content': 'Room does not exist.'})
            return
        room = rooms[room_id]
        if username not in room['members']:
            send_response(websocket, {'action': 'system', 'content': 'You are not a member of this room.'})
            return
        if message == '/keywords':
            context = ' '.join(msg['message'] for msg in room['history'][-50:])
            tokens = re.findall(r'\w+', context.lower())
            stopwords = {
                'the',
                'is',
                'and',
                'to',
                'a',
                'of',
                'in',
                'for',
                'on',
                'it',
                'this',
                'that',
                'you',
                'i',
            }
            terms = [t for t in tokens if t not in stopwords and len(t) > 1]

            top = Counter(terms).most_common(5)
            top_fmt = ', '.join(f'{w}({c})' for w, c in top) if top else 'No keywords found.'

            send_response(websocket, {'action': 'system', 'content': f'Top keywords: {top_fmt}'})
            return

        room['history'].append(
            {
                'user': username,
                'message': message,
                'time': round(time(), 3),
                'sentiment': do_s_ana(message),
            }
        )
        for member in room['members']:
            if member in name2websocket:
                send_response(
                    name2websocket[member],
                    {'action': 'new_message', 'content': {'room_id': room_id, **room['history'][-1]}},
                )

        if message.startswith('@bot ') or message in ['/summary']:
            try:
                asyncio.create_task(bot_response(websocket, room['history'], room_id, username))
            except Exception as e:
                print(f'Error in bot response: {e}')

    elif action == 'bot_response':
        room_id = content.get('room_id')
        message = content.get('response')
        room = rooms.get(room_id, None)
        if room is None:
            return
        room['history'].append({'user': 'bot', 'message': message, 'time': round(time(), 3)})
        for member in room['members']:
            if member in name2websocket:
                send_response(
                    name2websocket[member],
                    {'action': 'new_message', 'content': {'room_id': room_id, **room['history'][-1]}},
                )
    elif action == 'bot_personality_set':
        name2botpersonality[username] = content
        send_response(
            websocket,
            {'action': 'bot_personality_set', 'content': content},
        )
    elif action == 'history':
        room_id = content
        if room_id not in rooms:
            send_response(websocket, {'action': 'system', 'content': 'Room does not exist.'})
            return
        room = rooms[room_id]
        if username not in room['members']:
            send_response(websocket, {'action': 'system', 'content': 'You are not a member of this room.'})
            return
        send_response(
            websocket,
            {'action': 'history', 'content': {'room_id': room_id, 'history': room['history'][-100:]}},
        )
    elif action == 'invite_game':
        target_username = content.get('target_user')
        if target_username not in name2websocket:
            send_response(
                websocket, {'action': 'system_message', 'content': f'User {target_username} is not online.'}
            )
            return
        target_ws = name2websocket[target_username]
        pending_game_invites[username] = target_username
        send_response(target_ws, {'action': 'game_invited', 'content': {'inviter': username}})
        send_response(
            websocket, {'action': 'system_message', 'content': f'Game invitation sent to {target_username}.'}
        )
    elif action == 'game_response':
        print(111, pending_game_invites)
        inviter = content.get('target_user')
        response = content.get('response')
        if inviter not in pending_game_invites or pending_game_invites[inviter] != username:
            send_response(
                websocket,
                {'action': 'system_message', 'content': f'No pending game invitation from {inviter}.'},
            )
            return
        inviter_websocket = name2websocket.pop(inviter)
        if not inviter_websocket:
            send_response(
                websocket,
                {'action': 'system_message', 'content': f'User {inviter} is no longer online.'},
            )
            return
        if response == 'accepted':
            global GAME_ID_COUNTER
            current_game_id = GAME_ID_COUNTER
            GAME_ID_COUNTER += 1
            send_response(
                inviter_websocket,
                {
                    'action': 'game_start',
                    'content': {'player_id': 0, 'opponent': username, 'game_id': current_game_id},
                },
            )
            send_response(
                inviter_websocket,
                {
                    'action': 'system_message',
                    'content': f'{username} accepted your game invitation. Game ID: {current_game_id}',
                },
            )
            send_response(
                websocket,
                {
                    'action': 'game_start',
                    'content': {'player_id': 1, 'opponent': inviter, 'game_id': current_game_id},
                },
            )
            send_response(
                websocket,
                {
                    'action': 'system_message',
                    'content': f'You accepted the game invitation from {inviter}. Game ID: {current_game_id}',
                },
            )
        elif response == 'rejected':
            send_response(
                inviter_websocket,
                {'action': 'system_message', 'content': f'{username} rejected your game invitation.'},
            )
            send_response(
                websocket,
                {'action': 'system_message', 'content': f'You rejected the game invitation from {inviter}.'},
            )
    else:
        print(f'Unknown action: {action}')


async def handle_connection(websocket):
    print('Client connected')
    try:
        async for message in websocket:
            data = json.loads(message)
            await action_handler(websocket, data)
            # send_response(websocket, {"status": "ok", "received": data})
    except websockets.ConnectionClosed:
        username = getattr(websocket, 'username', None)
        if username and username in name2websocket:
            del name2websocket[username]
        print('Client disconnected')


async def periodic_save():
    while True:
        await asyncio.to_thread(save)
        await asyncio.sleep(5)


async def main():
    asyncio.create_task(periodic_save())
    server = await websockets.serve(handle_connection, 'localhost', 8766)
    print('WebSocket started, listening localhost:8766')
    await server.wait_closed()


if __name__ == '__main__':
    if (path / 'rooms.json').exists():
        with open(path / 'rooms.json', 'r', encoding='utf-8') as f:
            rooms = json.load(f)
    for i in rooms.keys():
        if int(i) > NUM:
            NUM = int(i)
    import threading
    from gameserver import main as game_main

    thread = threading.Thread(target=game_main, daemon=True)
    thread.start()
    asyncio.run(main())
