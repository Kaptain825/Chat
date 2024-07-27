import threading
import socket
import tkinter as tk
from tkinter import scrolledtext, simpledialog
import random 

def handle(socket1, text_area):
    while True:
        try:
            message = socket1.recv(1024).decode("utf-8")
            type = message[0]
            message = message[1:]
            key = socket1.recv(1024).decode("utf-8")
            d_key = int(key)
            d_message = caesar_decrypt(message, d_key)
            if d_message:
                text_area.config(state=tk.NORMAL)
                if type == 'p':
                    text_area.insert(tk.END, d_message + '\n', 'private')
                elif type == 'f':
                    text_area.insert(tk.END, d_message + '\n', 'self')
                elif type == 's':
                    text_area.insert(tk.END, d_message + '\n', 'system')
                else:
                    text_area.insert(tk.END, d_message + '\n')
                text_area.config(state=tk.DISABLED)
                text_area.yview(tk.END)
            else:
                break
        except Exception as e:
            print(f"Error from {socket1}: {e}")
            socket1.close()
            break

def send_message(sock, choice, message, key):
    try:
        sock.send(choice.encode("utf-8"))
        sock.send(message.encode("utf-8"))
        sock.send(key.encode("utf-8"))
    except Exception as e:
        print(f"Error sending message: {e}")

def caesar_encrypt(message, key):
    encrypted_message = ""
    for char in message:
        if char.isalpha():
            shift = ord('A') if char.isupper() else ord('a')
            encrypted_message += chr((ord(char) - shift + key) % 26 + shift)
        else:
            encrypted_message += char
    return encrypted_message

def caesar_decrypt(ciphertext, key):
    decrypted_message = ""
    for char in ciphertext:
        if char.isalpha():
            shift = ord('A') if char.isupper() else ord('a')
            decrypted_message += chr((ord(char) - shift - key) % 26 + shift)
        else:
            decrypted_message += char
    return decrypted_message

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('172.22.138.170', 54321))

    root = tk.Tk()
    root.title("Chat Application")

    nickname = simpledialog.askstring("Nickname", "Enter your nickname:")
    client_socket.send(nickname.encode("utf-8"))

    root.title(f"Chat Application - {nickname}")

    text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, state=tk.DISABLED)
    text_area.pack(padx=20, pady=5)

    text_area.tag_configure('self', foreground='darkblue')
    text_area.tag_configure('private', foreground='red')
    text_area.tag_configure('system', foreground='darkgreen')

    message_entry = tk.Entry(root, width=50)
    message_entry.pack(padx=20, pady=5)

    choice_entry = tk.Entry(root, width=10)
    choice_entry.pack(padx=10, pady=2)

    def on_send():
        message = message_entry.get()
        message = f"{nickname}:{message}"
        choice = choice_entry.get()
        key = random.randint(-25, 25)

        e_message = caesar_encrypt(message, key)
        s_key = str(key)

        if message.lower() == "close":
            client_socket.send(choice.encode("utf-8"))
            client_socket.send(message.encode("utf-8"))
            client_socket.close()
            root.quit()
        else:
            send_message(client_socket, choice, e_message, s_key)
            message_entry.delete(0, tk.END)
            choice_entry.delete(0, tk.END)

    def help1():
        send_message(client_socket, "2018", "/help", "0")

    send_button = tk.Button(root, text="Send", command=on_send)
    send_button.pack(padx=20, pady=5)

    help_button = tk.Button(root, text="Help", command=help1)
    help_button.pack(padx=10, pady=2.5)

    t1 = threading.Thread(target=handle, args=(client_socket, text_area))
    t1.start()

    root.protocol("WM_DELETE_WINDOW", lambda: (client_socket.close(), root.quit()))
    root.mainloop()

main()
