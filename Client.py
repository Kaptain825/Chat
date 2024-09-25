import threading
import socket
import tkinter as tk
from tkinter import scrolledtext, simpledialog, filedialog
from tkinter import ttk
import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import base64

last_chosen_recipient = "Everyone"  

def handle(socket1, text_area, recipient_combobox):
    while True:
        try:
            message = socket1.recv(1024).decode("utf-8")
            if message.startswith('file|'):
                parts = message.split('|')
                file_name = parts[1]
                file_size = int(parts[2])
                file_content = b''
                while len(file_content) < file_size:
                    file_content += socket1.recv(min(file_size - len(file_content), 1024))
                save_path = filedialog.asksaveasfilename(initialfile=file_name)
                if save_path:
                    with open(save_path, 'wb') as f:
                        f.write(file_content)
                    text_area.config(state=tk.NORMAL)
                    text_area.insert(tk.END, f'File received: {file_name}\n', 'file')
                    text_area.config(state=tk.DISABLED)
                    text_area.yview(tk.END)
            else:
                parts = message.split('|')
                if len(parts) != 4:
                    continue
                type = parts[0]
                encrypted_message = parts[1]
                key = parts[2]
                iv = parts[3]
                if type == 's':
                    d_message = encrypted_message 
                    nicknames = extract_nicknames(d_message)
                    recipient_combobox['values'] = nicknames + ["Everyone"]
                else:
                    d_message = decrypt(encrypted_message, key, iv)

                if d_message:
                    text_area.config(state=tk.NORMAL)
                    if type == 'p':
                        text_area.insert(tk.END, d_message + '\n', 'private')
                    elif type == 'f':
                        text_area.insert(tk.END, d_message + '\n', 'self')
                    text_area.config(state=tk.DISABLED)
                    text_area.yview(tk.END)
        except Exception as e:
            print(f"Error from {socket1}: {e}")
            socket1.close()
            break

def extract_nicknames(message):
    parts = message.split('|')
    nickname_parts = parts[1:-2]
    nicknames = [part.split(':')[1] for part in nickname_parts]
    return nicknames

def send_message(sock, recipient, message, key, iv):
    try:
        full_message = f"{recipient}|{message}|{key}|{iv}"
        sock.send(full_message.encode("utf-8"))
    except Exception as e:
        print(f"Error sending message: {e}")

def send_file(sock, file_path, recipient):
    try:
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        sock.send(f"file|{file_name}|{file_size}|{recipient}".encode("utf-8"))
        with open(file_path, 'rb') as f:
            while chunk := f.read(1024):
                sock.send(chunk)
    except Exception as e:
        print(f"Error sending file: {e}")

def encrypt(text):
    key = get_random_bytes(16)  
    iv = get_random_bytes(AES.block_size) 

    key_base64 = base64.b64encode(key).decode('utf-8')
    iv_base64 = base64.b64encode(iv).decode('utf-8')

    data = text.encode('utf-8')
    padded = pad(data, AES.block_size)

    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(padded)

    return (
        base64.b64encode(ciphertext).decode('utf-8'),
        key_base64,
        iv_base64
    )

def decrypt(ciphertext, key, iv):
    key = base64.b64decode(key)
    iv = base64.b64decode(iv)
    ciphertext = base64.b64decode(ciphertext)
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = cipher.decrypt(ciphertext)

    try:
        text = unpad(padded, AES.block_size)
    except ValueError:
        print("Incorrect padding")
        return None

    return text.decode('utf-8')

def main():
    global last_chosen_recipient

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('172.22.138.170', 54321))

    root = tk.Tk()
    root.title("Chat Application")

    nickname = simpledialog.askstring("Nickname", "Enter your nickname:")
    client_socket.send(nickname.encode("utf-8"))

    root.title(f"Chat Application - {nickname}")

    frame = tk.Frame(root)
    frame.grid(row=0, column=0, sticky="nsew")

    text_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state=tk.DISABLED)
    text_area.grid(row=0, column=0, padx=20, pady=5, sticky="nsew")

    text_area.tag_configure('self', foreground='darkblue')
    text_area.tag_configure('private', foreground='red')
    text_area.tag_configure('file', foreground='purple')

    bottom_frame = tk.Frame(root)
    bottom_frame.grid(row=1, column=0, sticky="ew")

    message_entry = tk.Entry(bottom_frame, width=50)
    message_entry.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

    recipient_combobox = ttk.Combobox(bottom_frame, state="readonly")
    recipient_combobox.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
    recipient_combobox['values'] = [last_chosen_recipient]  
    recipient_combobox.set(last_chosen_recipient)

    def on_send():
        global last_chosen_recipient
        message = message_entry.get()
        message = f"{nickname}:{message}"
        recipient = recipient_combobox.get()

        e_message, key, iv = encrypt(message)

        if message.lower() == "close":
            send_message(client_socket, recipient, e_message, key, iv)
            client_socket.close()
            root.quit()
        else:
            send_message(client_socket, recipient, e_message, key, iv)
            message_entry.delete(0, tk.END)
            last_chosen_recipient = recipient  

    def on_send_file():
        file_path = filedialog.askopenfilename()
        if file_path:
            recipient = recipient_combobox.get()  
            send_file(client_socket, file_path, recipient)

    def help1():
        send_message(client_socket, "2018", "/help", "0", "0")

    def set_placeholder(entry, placeholder_text):
        def on_focus_in(event):
            if entry.get() == placeholder_text:
                entry.delete(0, tk.END)
                entry.config(fg='black')

        def on_focus_out(event):
            if entry.get() == '':
                entry.insert(0, placeholder_text)
                entry.config(fg='grey')

        entry.insert(0, placeholder_text)
        entry.config(fg='grey')
        entry.bind('<FocusIn>', on_focus_in)
        entry.bind('<FocusOut>', on_focus_out)

    set_placeholder(message_entry, "Type your message here...")

    send_button = tk.Button(bottom_frame, text="Send", command=on_send)
    send_button.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

    file_button = tk.Button(bottom_frame, text="Send File", command=on_send_file)
    file_button.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

    help_button = tk.Button(bottom_frame, text="Help", command=help1)
    help_button.grid(row=1, column=2, padx=10, pady=5, sticky="ew")

    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    t1 = threading.Thread(target=handle, args=(client_socket, text_area, recipient_combobox))
    t1.start()

    root.protocol("WM_DELETE_WINDOW", lambda: (client_socket.shutdown(socket.SHUT_RDWR), client_socket.close(), root.quit()))
    root.mainloop()

main()
