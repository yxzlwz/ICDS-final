import socket
import pickle

class Network:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = "10.209.93.40"  
        self.port = 5555
        self.p = self.connect()

    def connect(self):
        try:
            self.client.connect((self.server, self.port))
            return self.client.recv(2048).decode() 
        except socket.error as e:
            print(f"Connection error: {e}")
            return None

    def getP(self):
        return self.p

    def send(self, data):
        try:
            self.client.sendall(str(data).encode())
            recv_data = self.client.recv(2048*2)
            return pickle.loads(recv_data)
        except Exception as e:
            print(f"Send error: {e}")
            return None