import socket
import threading
i=0

def handle(client_socket, client_address, client_nicknames):
    global i
    while True:
        try:
            client_socket.sendall("choose".encode("utf-8"))
            client_info = ""
            for c in client_nicknames:
                client_info = client_info+f"{i+1}:{c}"+" "
                i=i+1

            client_socket.sendall(client_info.encode("utf-8"))
            
            message = client_socket.recv(1024).decode("utf-8")
            if not message:
                raise Exception("Disconnected")
            
            selection = int(message[0]) 

            if selection == 4:
                broadcast_message = message[2:]
                broad(client_nicknames, client_socket, broadcast_message)
            
            elif 0 < selection <= len(client_nicknames):
                recipient_socket = client_sockets[selection - 1]
                forward_message = f"{message[1:]}"
                recipient_socket.sendall(forward_message.encode("utf-8"))
        
        except Exception as e:
            disconnection(client_socket, client_nicknames)
            break

def disconnection(client_socket, client_nicknames):
    try:
        client_index = client_sockets.index(client_socket)
        disconnected_client = client_nicknames.pop(client_index)
        client_sockets.remove(client_socket)
        client_socket.close()
        broad(client_nicknames, f"Device {disconnected_client} has disconnected...")
    except ValueError:
        pass

def broad(client_nicknames, sender_socket, message):
    for socket_ in client_sockets:
        if socket_ != sender_socket:
            socket_.sendall(message.encode("utf-8"))

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostbyname(socket.gethostname())
    port = 54321

    server_socket.bind((host, port))
    server_socket.listen()

    print("Server is listening...")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"New connection from {client_address}")
        client_sockets.append(client_socket)

        client_socket.sendall("Enter your nickname: ".encode("utf-8"))
        nickname = client_socket.recv(1024).decode("utf-8")
        client_nicknames.append(nickname)

        broad(client_nicknames, client_socket, f"{nickname} has now connected...")

        thread = threading.Thread(target=handle, args=(client_socket, client_address, client_nicknames))
        thread.start()

client_sockets = []
client_nicknames = []
main()
