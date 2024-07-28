import socket
import threading

lock = threading.Lock()

def handle(client_socket, nicknames, sockets):
    try:
        while True:
            full_message = client_socket.recv(1024).decode('utf-8')
            if full_message.startswith('file|'):
                parts = full_message.split('|')
                if len(parts) != 4:
                    continue
                file_name = parts[1]
                file_size = int(parts[2])
                recipient_index = int(parts[3])
                file_content = b''
                while len(file_content) < file_size:
                    file_content += client_socket.recv(min(file_size - len(file_content), 1024))
                if 0 <= recipient_index < len(sockets):
                    recipient_socket = sockets[recipient_index]
                    recipient_socket.send(f"file|{file_name}|{file_size}".encode('utf-8'))
                    recipient_socket.send(file_content)
                else:
                    broad(f"file|{file_name}|{file_size}".encode('utf-8'), sockets)
                    broad(file_content, sockets)
            else:
                parts = full_message.split('|')
                if len(parts) != 3:
                    continue
                choice, message, key = parts
                choice = int(choice)
                if 0 <= choice < len(sockets):
                    receiver = sockets[choice]
                    receiver.send(f"p|{message}|{key}".encode('utf-8'))
                    client_socket.send(f"f|{message}|{key}".encode('utf-8'))
                elif choice == len(sockets):
                    broad(f"a|{message}|{key}".encode('utf-8'), sockets)
                elif choice == 2018:
                    txt = "s|"
                    i = 0
                    for x in nicknames:
                        txt += f"{i}:{x} "
                        i += 1
                    txt += f"{len(nicknames)}:Everyone|0"
                    client_socket.send(txt.encode('utf-8'))
                else:
                    break
    except Exception as e:
        print("Error: ", e)
    finally:
        with lock:
            i = sockets.index(client_socket)
            del nicknames[i]
            del sockets[i]
            client_socket.close()

def broad(message, sockets):
    with lock:
        for sock in sockets:
            try:
                sock.send(message)
            except Exception as e:
                print("Error:", e)

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostbyname(socket.gethostname())
    port = 54321
    server_socket.bind((host, port))
    server_socket.listen()
    print("Server is listening...")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"{client_socket} has connected...")

        nick = client_socket.recv(1024).decode('utf-8')

        with lock:
            nicknames.append(nick)
            sockets.append(client_socket)

        t1 = threading.Thread(target=handle, args=(client_socket, nicknames, sockets))
        t1.start()

nicknames = []
sockets = []

main()
