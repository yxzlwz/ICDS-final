# ICDS Final Project

## Run

### Install Requirements

```bash
pip install -r requirements.txt
```

### Server

```bash
python server.py
```

### Client

```bash
python gui.py
```

## Modify

### Server Side

- Modify `action_handler` in `server.py` to add new actions.
- Use `send_response` to send data back to the client.

### Client Side

- Modify `event_handler` in class `ChatApp` in `gui.py` to process server responses.
- Use `send` to send data to the server.
  - For most times, call `send(action, content)` is enough. However, if an error occurs, you may need to call `send(action, content, sync=False)`.
