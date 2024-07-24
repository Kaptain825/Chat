import socket
import threading

lock = threading.Lock()

def handle(client_socket, nicknames, sockets):
    try:
        while True:
            choice = client_socket.recv(1024).decode('utf-8')
            message = client_socket.recv(1024).decode('utf-8')
            print(choice+" ")
            print(message)
            choice = int(choice)
            if 0 <= choice < len(sockets):
                    receiver = sockets[choice]
                    sender_nickname = nicknames[sockets.index(client_socket)]
                    receiver.send(f"p{sender_nickname}: {message}".encode('utf-8'))
                    client_socket.send(f"f{sender_nickname}: {message}".encode('utf-8'))
            elif choice == len(sockets):
                    broad(f"{nicknames[sockets.index(client_socket)]}: {message}".encode('utf-8'), sockets)
            elif choice == 2018:
                txt = "s"
                i = 0
                for x in nicknames:
                    txt = txt+f"{i}:{x} "
                    i=i+1
                txt += f"{len(nicknames)}:Everyone"
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
