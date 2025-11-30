from ollama import Client
from openai import OpenAI


class ChatBotClient():
    """
    A chatbot client using Ollama for local model inference.
    Supports personality customization and conversation history management.
    """

    def __init__(self, name="Assistant", model="phi3:mini", host='http://localhost:11434', 
                 headers={'x-some-header': 'some-value'}, personality="friendly and helpful"):
        """
        Initialize the chatbot client.
        
        Args:
            name (str): Name of the chatbot
            model (str): Ollama model name to use (default: phi3:mini)
            host (str): Ollama server host URL
            headers (dict): Additional headers for the client
            personality (str): Description of the bot's personality
        """
        self.host = host
        self.name = name
        self.model = model
        self.personality = personality
        self.client = Client(host=self.host, headers=headers)
        # Initialize system message with personality
        self.messages = [
            {
                "role": "system", 
                "content": f"You are {name}, a helpful AI assistant. Your personality is: {personality}. Keep responses concise and engaging."
            }
        ]
    
    def update_personality(self, new_personality):
        """
        Update the bot's personality and refresh the system message.
        
        Args:
            new_personality (str): New personality description
        """
        self.personality = new_personality
        # Update system message with new personality
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = f"You are {self.name}, a helpful AI assistant. Your personality is: {self.personality}. Keep responses concise and engaging."
        else:
            self.messages.insert(0, {
                "role": "system", 
                "content": f"You are {self.name}, a helpful AI assistant. Your personality is: {self.personality}. Keep responses concise and engaging."
            })
    
    def chat(self, message: str):
        """
        Send a message to the chatbot and get the response.
        Maintains conversation history with length limiting.
        
        Args:
            message (str): User's input message
            
        Returns:
            str: Bot's response text
        """
        # Add user message to conversation history
        self.messages.append({"role": "user", "content": message})

        try:
            # Get response from Ollama
            response = self.client.chat(
                self.model,
                messages=self.messages
            )
            msg = response["message"]["content"]

            # Add assistant's response to conversation history
            self.messages.append({"role": "assistant", "content": msg})
            
            # Limit conversation history length (keep last 10 exchanges)
            if len(self.messages) > 21:  # 1 system message + 10 exchanges (2 messages each)
                self.messages = [self.messages[0]] + self.messages[-20:]
                
            return msg
        except Exception as e:
            return f"Error: {str(e)}"
    
    def stream_chat(self, message):
        """
        Stream the chatbot response for real-time display.
        
        Args:
            message (str): User's input message
        """
        # Add user message to conversation history
        self.messages.append({
            'role': 'user',
            'content': message,
        })
        
        # Stream response from Ollama
        response = self.client.chat(self.model, self.messages, stream=True)
        answer = ""
        for chunk in response:
            piece = chunk["message"]["content"]
            print(piece, end="")
            answer += piece
        
        # Add assistant's response to conversation history
        self.messages.append({"role": "assistant", "content": answer})
        
        # Limit conversation history length
        if len(self.messages) > 21:
            self.messages = [self.messages[0]] + self.messages[-20:]


class ChatBotClientOpenAI():
    """
    A chatbot client using OpenAI-compatible APIs.
    Suitable for ChatGPT API or any OpenAI-compatible endpoints.
    """
    
    def __init__(self, name="3po", model="phi3:mini", host='http://localhost:11434', headers={'x-some-header': 'some-value'}):
        """
        Initialize the OpenAI-compatible chatbot client.
        
        Args:
            name (str): Name of the chatbot
            model (str): Model identifier
            host (str): API server host URL
            headers (dict): Additional headers for the client
        """
        self.host = host
        self.name = name
        self.model = model
        self.client = OpenAI(api_key="EMPTY", base_url="http://10.209.93.21:8000/v1")  # use other port if necessary
        self.messages = []

    def chat(self, messages):
        """
        Send messages to the OpenAI-compatible API and get response.
        
        Args:
            messages (list): List of message dictionaries with role and content
            
        Returns:
            str: Model's response text
        """
        model_id = "/home/nlp/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/7ae557604adf67be50417f59c2c2f167def9a775"
        # Example system prompt (commented out):
        # messages = [
        #     {"role": "system", "content": f"Enter role play mode. You are {self.name}, a professional academic advisor at NYU Shanghai. Reply warmly, within 20 words."},
        #     {"role": "user", "content": query + "/no_think"},
        # ]

        response = self.client.chat.completions.create(
            messages=messages,
            model=model_id,
            temperature=0.3,
        )
        return response.choices[0].message.content
    

if __name__ == "__main__":
    # Test the ChatBotClient with phi3:mini
    c = ChatBotClient()
    print("Testing ChatBotClient with phi3:mini...")
    print(c.chat("Your name is Tom, and you are the learning assistant of Python programming."))
    print(c.stream_chat("What's your name and role?"))
    
    # Test personality update
    c.update_personality("professional and technical")
    print(c.chat("How would you describe your personality?"))