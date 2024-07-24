import socket
import threading

def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode("utf-8")
            print("\n")
            print(message)
            print("\n")
        except Exception as e:
            print("Error:", e)
            client_socket.close()
            break

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('172.22.138.170', 54321))

    nickname = input("Enter your nickname:")
    print("\n")

    client_socket.sendall(nickname.encode("utf-8"))

    receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
    receive_thread.start()

    while True:
        recipient = input("Enter the device you want to send to (4 for all devices): ")
        message = input("Enter the message you want to send: ")

        if message.lower() == "close":
            client_socket.sendall(f"{nickname} is disconnecting...".encode("utf-8"))
            client_socket.close()
            break

        client_socket.sendall(f"{recipient}{nickname}: {message}".encode("utf-8"))


main()