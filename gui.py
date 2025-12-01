import tkinter as tk
from tkinter import simpledialog, messagebox
from time import ctime
import subprocess

# Import ChatBotClient for AI chatbot functionality

EH = None
send = None


class ChatApp:
    chat_target = None
    bot_personality = ''

    def __init__(self, root):
        self.root = root
        self.root.title('Chat Application')

    def login(self):
        self.username = None
        while self.username is None:
            self.username = simpledialog.askstring('Login', 'Enter your username:')
            if not self.username:
                messagebox.showerror('Error', 'Username cannot be empty!')
        send('login', self.username)
        self.login_popup = tk.Toplevel(self.root)
        self.login_popup.title('Logging In')
        self.login_popup.geometry('200x100')
        tk.Label(self.login_popup, text='Logging in...').pack(expand=True)
        self.root.update_idletasks()

    def finish_login(self):
        self.login_popup.destroy()

        self.root.title(f'Chat Application - login as {self.username}')
        # Main layout frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill='both', expand=True)

        # Left frame for chat target selection
        left_frame = tk.Frame(main_frame, width=150)
        left_frame.pack(side='left', fill='y')

        # Chat Targets label and refresh button
        label_frame = tk.Frame(left_frame)
        label_frame.pack(fill='x', padx=5, pady=5)

        self.chat_target_label = tk.Label(label_frame, text='Contact')
        self.chat_target_label.pack(side='left')

        self.refresh_button = tk.Button(label_frame, text='Refresh', command=self.refresh_chat_targets)
        self.refresh_button.pack(side='right')
        self.create_button = tk.Button(label_frame, text='Create', command=self.open_create_room_dialog)
        self.create_button.pack(side='right')

        self.game_button = tk.Button(left_frame, text='invite game', command=self.invite_game)
        self.game_button.pack(pady=5)

        self.room_listbox = tk.Listbox(left_frame, height=20)
        self.room_listbox.pack(padx=5, pady=5, fill='both', expand=True)

        # Example targets (these can be dynamically updated)
        example_targets = ['User1', 'User2', 'User3']
        for target in example_targets:
            self.room_listbox.insert(tk.END, target)

        self.room_listbox.bind('<<ListboxSelect>>', self.select_chat_target)

        # Right frame for chat display and input
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side='right', fill='both', expand=True)

        # Button row above chat display area
        button_row = tk.Frame(right_frame)
        button_row.pack(fill='x', padx=10, pady=5)

        sonnet_button = tk.Button(button_row, text='Sonnet', command=lambda: self.handle_action('sonnet'))
        sonnet_button.pack(side='left', padx=5)

        time_button = tk.Button(button_row, text='Time', command=lambda: self.handle_action('time'))
        time_button.pack(side='left', padx=5)

        personality_button = tk.Button(
            button_row, text='Set Bot Personality', command=lambda: self.handle_action('set_personality')
        )
        personality_button.pack(side='left', padx=5)

        # Chat display area
        self.chat_display = tk.Text(right_frame, state='disabled', wrap='word', height=20, width=50)
        self.chat_display.pack(padx=10, pady=10, expand=True, fill='both')

        self.chat_display.tag_configure('from-you', justify='right')
        self.chat_display.tag_configure('sentiment-positive', foreground='red')
        self.chat_display.tag_configure('sentiment-negative', foreground='green')
        self.chat_display.tag_configure('sentiment-neutral', foreground='blue')
        self.chat_display.tag_configure('user_question', foreground='blue', font=('Arial', 10, 'bold'))
        self.chat_display.tag_configure('user_question_text', foreground='darkblue')
        self.chat_display.tag_configure('bot_response', foreground='green', font=('Arial', 10, 'bold'))
        self.chat_display.tag_configure('bot_response_text', foreground='darkgreen')

        # Input field
        self.input_field = tk.Entry(right_frame, width=40)
        self.input_field.pack(side='left', padx=5, pady=10, expand=True, fill='x')
        self.input_field.bind('<Return>', self.send_message)

        # Send button
        self.send_button = tk.Button(right_frame, text='Send', command=self.send_message)
        self.send_button.pack(side='right', padx=5, pady=10)
        emoji_button = tk.Button(right_frame, text='😊', command=self.open_emoji_selector)
        emoji_button.pack(side='right')
        # Adjust window size
        self.root.geometry('800x500')

        send('my_room_list', sync=False)

    def send_message(self, event=None):
        message = self.input_field.get()
        if not message.strip():
            return

        send('send_message', {'room_id': self.chat_target, 'message': message})

        self.input_field.delete(0, tk.END)

    def display_message(self, sender, message, sentiment=None):
        """Display message in chat area with sender identification"""
        self.chat_display.config(state='normal')

        # 为不同的发送者使用不同的格式
        if sender == 'You (to Bot)':
            # 用户给机器人的问题用特殊格式显示
            self.chat_display.insert(tk.END, '➤ You asked Bot:\n', 'user_question')
            self.chat_display.insert(tk.END, f'{message}\n\n', 'user_question_text')
        elif sender == 'ChatBot':
            # 机器人的回答用特殊格式显示
            self.chat_display.insert(tk.END, '🤖 Bot replied:\n', 'bot_response')
            self.chat_display.insert(tk.END, f'{message}\n\n', 'bot_response_text')
        else:
            # 普通消息保持原有格式
            if self.username == sender:
                self.chat_display.insert(tk.END, f'[You]\n{message}\n', 'from-you')
                if sentiment:
                    self.chat_display.insert(
                        tk.END, f'Sentiment: {sentiment}\n', [f'sentiment-{sentiment}', 'from-you']
                    )
                self.chat_display.insert(tk.END, '\n')
            else:
                self.chat_display.insert(tk.END, f'[{sender}]\n{message}\n')
                if sentiment:
                    self.chat_display.insert(tk.END, f'Sentiment: {sentiment}\n', f'sentiment-{sentiment}')
                self.chat_display.insert(tk.END, '\n')

        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)

    def select_chat_target(self, event, sync=True):
        # Handle chat target selection
        selected_target = self.room_listbox.get(self.room_listbox.curselection())
        print(selected_target)
        room_id = selected_target.split(']')[0][1:]
        self.chat_target = room_id
        self.chat_display.config(state='normal')
        self.chat_display.delete(1.0, tk.END)

        self.chat_display.config(state='disabled')
        send('history', room_id, sync=sync)

    def refresh_chat_targets(self):
        self.room_listbox.delete(0, tk.END)
        send('my_room_list')

    def invite_game(self):
        if not self.chat_target:
            messagebox.showerror('Error', 'Please select a chat room/user to invite.')
        room_info = None
        for item in self.room_listbox.get(0, tk.END):
            if item.startswith(f'[{self.chat_target}]'):
                room_info = item
                break
        if not room_info:
            messagebox.showerror('Error', 'Selected chat room/user not found.')
            return
        users_str = room_info.split('] ')[1]
        users = [u.strip() for u in users_str.split(',')]
        target_user = next((u for u in users if u != self.username), None)
        if not target_user:
            messagebox.showerror('Error', 'Only two-person chats can invite games.')
            return
        send('invite_game', {'target_user': target_user})
        messagebox.showinfo('Game Invite', f'Sent game invitation to {target_user}...')

    def start_game_client(self, content_dict):
        player_id = content_dict.get('player_id')
        game_id = content_dict.get('game_id')
        game_client_path = './gameclient.py'
        if player_id is None or game_id is None:
            messagebox.showerror('Error', 'Missing player_id or game_id from server content.')
            return
        try:
            subprocess.Popen(['python3', game_client_path, str(player_id), str(game_id)])
            messagebox.showinfo('Game Started', f'Game started for player {player_id}.')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to start game client: {e}')

    def event_handler(self, action, content):
        """
        Handle incoming events from the server.
        Extended to handle bot-related actions.
        """
        if action == 'system':
            self.display_message('SYSTEM', content)
        elif action == 'login':
            self.finish_login()
        elif action == 'user_list':
            for user in content:
                try:
                    self.user_listbox.insert(tk.END, user)
                except Exception:
                    break
        elif action == 'my_room_list':
            self.room_listbox.delete(0, tk.END)
            for room in content:
                try:
                    self.room_listbox.insert(tk.END, room)
                except Exception:
                    break
        elif action == 'switch_room':
            # self.chat_target_listbox.activate()
            room_id = content
            self.room_listbox.selection_clear(0, tk.END)
            for idx in range(self.room_listbox.size()):
                if self.room_listbox.get(idx).startswith(f'[{room_id}]'):
                    self.room_listbox.selection_set(idx)
                    self.select_chat_target(None, False)
        elif action == 'history':
            if self.chat_target != content['room_id']:
                return
            self.chat_display.delete(1.0, tk.END)
            # 配置文本样式
            self.chat_display.tag_configure('user_question', foreground='blue', font=('Arial', 10, 'bold'))
            self.chat_display.tag_configure('user_question_text', foreground='darkblue')
            self.chat_display.tag_configure('bot_response', foreground='green', font=('Arial', 10, 'bold'))
            self.chat_display.tag_configure('bot_response_text', foreground='darkgreen')

            for msg in content['history']:
                self.display_message(msg['user'], msg['message'], msg.get('sentiment'))
        elif action == 'new_message':
            if self.chat_target != content['room_id']:
                return
            self.display_message(content['user'], content['message'], content.get('sentiment'))
        elif action == 'game_invited':
            inviter = content.get('inviter')
            accept = messagebox.askyesno(
                'Game Invitation', f'You have been invited to a game by {inviter}. Do you want to join?'
            )
            if accept:
                send('game_response', {'target_user': inviter, 'response': 'accepted'})
            else:
                send('game_response', {'target_user': inviter, 'response': 'declined'})
        elif action == 'game_start':
            self.start_game_client(content)
        elif action == 'system_message':
            self.display_message('SYSTEM', content)
        # Add bot-related action handlers
        elif action == 'bot_personality_set':
            messagebox.showinfo('ChatBot', f'Bot personality set to: {content}')

    def handle_action(self, action):
        """
        Handle button actions, extended for bot functionality.
        """
        if action == 'sonnet':
            id = simpledialog.askinteger('Sonnet', 'Enter sonnet ID:', minvalue=1)
            send('sonnet', id)
        elif action == 'time':
            self.display_message('SYSTEM', f'Current time: {ctime()}')
        # Add bot-related actions
        elif action == 'set_personality':
            self.set_bot_personality()

    def set_bot_personality(self):
        self.bot_personality = simpledialog.askstring(
            'Bot Personality',
            "Describe the bot's personality (e.g., 'friendly and humorous', 'professional and concise'):",
            initialvalue=self.bot_personality,
        )

        send('bot_personality_set', self.bot_personality)

    def open_create_room_dialog(self):
        send('user_list')
        dialog = tk.Toplevel(self.root)
        dialog.title('Select Users')
        dialog.geometry('300x400')

        tk.Label(dialog, text='Select users:').pack(pady=10)

        self.user_listbox = tk.Listbox(dialog, selectmode='multiple', height=15)
        self.user_listbox.pack(padx=10, pady=10, fill='both', expand=True)

        def confirm_selection():
            selected_indices = self.user_listbox.curselection()
            selected_users = [self.user_listbox.get(i) for i in selected_indices]
            print('Selected users:', selected_users)
            send('create_room', selected_users)
            dialog.destroy()

        tk.Button(dialog, text='Confirm', command=confirm_selection).pack(pady=10)

    def open_emoji_selector(self):
        # Create a new modal dialog for emoji selection
        emoji_window = tk.Toplevel(self.root)
        emoji_window.title('Select Emoji')
        emoji_window.geometry('400x300')
        emoji_window.transient(self.root)  # Make it a modal dialog
        emoji_window.grab_set()  # Prevent interaction with other windows

        # List of emojis
        emojis = '😊😂👍😢😡🎉😎🤔🙌💯🔥✨🎶🥳🤩😇😴🤯🤗😬😱🤤😜'

        # Function to insert selected emoji into the input field
        def select_emoji(emoji):
            self.input_field.insert(tk.END, emoji)
            emoji_window.destroy()

        cols = 6
        for i, emoji in enumerate(emojis):
            btn = tk.Button(emoji_window, text=emoji, command=lambda e=emoji: select_emoji(e))
            btn.grid(row=i // cols, column=i % cols, padx=5, pady=5)


def run_async_loop():
    import asyncio
    from client import communicate, send as client_send

    global send
    send = client_send
    asyncio.run(communicate(EH))


if __name__ == '__main__':
    root = tk.Tk()
    app = ChatApp(root)
    EH = app.event_handler
    import threading

    thread = threading.Thread(target=run_async_loop, daemon=True)
    thread.start()
    app.login()
    root.mainloop()
