import threading
import socket
import tkinter as tk
from tkinter import scrolledtext, simpledialog, filedialog, ttk
import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import base64
import cx_Oracle
from datetime import datetime

#Database Setup
dsn = "localhost:1521/XE"
user = "system"
password = "mithun12"

#Variables to store last chosen user and to store user's nickname
last_recipient = "Everyone"
nickname = ""

def insert_message(message, recipient):
    try:
        print("Debug: Attempting to connect to the database...")
        with cx_Oracle.connect(user, password, dsn) as connection: #connecting to database
            print("Debug: Successfully connected to the database.")
            cursor = connection.cursor()
            date_time = datetime.now() #to current get date and time 
            sql = "INSERT INTO messages (MESSAGE, RECIPIENT, DATE_TIME) VALUES (:message, :recipient, :date_time)" #insert the message along with the recipient and date and time
            cursor.execute(sql, message=message, recipient=recipient, date_time=date_time) #executing the query
            connection.commit() #commiting the query so it changes will be stored.
            print(f"Debug: Message inserted into database - MESSAGE: {message}, RECIPIENT: {recipient}, DATE_TIME: {date_time}")
    except cx_Oracle.DatabaseError as e:
        print(f"Database error during insert_message: {e}")

def fetch_last_messages(nickname):
    messages = [] #list to store last 10 messages
    try:
        print("Debug: Attempting to connect to the database to fetch messages...")
        with cx_Oracle.connect(user, password, dsn) as connection:
            print("Debug: Successfully connected to the database.")
            cursor = connection.cursor()
            sql = "SELECT MESSAGE, DATE_TIME FROM (SELECT MESSAGE, DATE_TIME FROM messages WHERE RECIPIENT = :recipient ORDER BY DATE_TIME DESC) WHERE ROWNUM <= 10" #query to get last 10 messages from descending order
            cursor.execute(sql, recipient=nickname)
            messages = cursor.fetchall() #fetch all messages instead of 1 by 1
            print(f"Debug: Fetched {len(messages)} messages for recipient {nickname}.")
    except cx_Oracle.DatabaseError as e:
        print(f"Database error during fetch_last_messages: {e}")
    return messages

def display_last_messages(text_area, nickname):
    messages = fetch_last_messages(nickname)
    if messages:
        text_area.config(state=tk.NORMAL)
        print("Debug: Displaying last messages...")
        for message_with_date in reversed(messages):  # Reverse to display oldest firs
            message,date = message_with_date #message splits the message and date_time to just access the message alone.
            parts = message.split("|") #splits each message to get each part
            msg_type = parts[0] 
            encrypted_message = parts[1]
            key = parts[2]
            iv = parts[3]
            decrypted_message = encrypted_message if msg_type == 's' else decrypt(encrypted_message, key, iv)
            if decrypted_message:
                if msg_type == 'p':
                    text_area.insert(tk.END, decrypted_message + '\n', 'private')
                elif msg_type == 'f':
                    text_area.insert(tk.END, decrypted_message + '\n', 'self')
                else:
                    text_area.insert(tk.END, decrypted_message + '\n')
            else:
                print("Debug: Decryption failed or message is None")
                continue
        text_area.config(state=tk.DISABLED)
        text_area.yview(tk.END)
    else:
        print("Debug: No stored messages found.")
        
def handle(socket1, text_area, combobox,nickname):
    while True:
        try:
            message = socket1.recv(1024).decode("utf-8")
            print(f"Debug: Received message: {message}")

            if message.startswith('file|'):
                # Handle file transfer
                parts = message.split('|')
                file_name = parts[1]
                file_size = int(parts[2])
                file_content = b''

                while len(file_content) < file_size:
                    chunk = socket1.recv(min(file_size - len(file_content),65536)) #recieves the file data in 64kb and below chunks 
                    if not chunk:
                        print("Debug: Connection closed while receiving file content.")
                        return
                    file_content += chunk #and stitches it together

                save_path = filedialog.asksaveasfilename(initialfile=file_name) #line to choose where to store the file
                if save_path:
                    with open(save_path, 'wb') as f:
                        f.write(file_content) #writes the data into a file
                    text_area.config(state=tk.NORMAL)
                    text_area.insert(tk.END, f'File received: {file_name}\n', 'file')
                    text_area.config(state=tk.DISABLED)
                    text_area.yview(tk.END)

            else:
                parts = message.split('|')
                print(f"Debug: Parts after splitting: {parts}")

                if parts[0] == 's': #if s|-|-|- then its the server giving the nicknames of users online
                    nicknames = parts[1].split()
                    print(f"Debug: Nicknames list: {nicknames}")
                    combobox['values'] = nicknames #updates the dropdown recipient box with the online users there
                    if last_recipient in nicknames:
                        combobox.set(last_recipient) #if the last chosen user to send message to is in user it keeps it as that user
                    else:
                        combobox.set("Everyone") #else it defaults back to Everyone
                    continue

                if len(parts) != 4: #all parts did not arrive
                    print("Debug: Incorrect message format") 
                    continue
                
                print(f"nickname is: {nickname}\n")
                insert_message(message,nickname)
                msg_type = parts[0]
                encrypted_message = parts[1]
                key = parts[2]
                iv = parts[3]

                print(f"Debug: Type: {msg_type}, Encrypted Message: {encrypted_message}, Key: {key}, IV: {iv}")

                decrypted_message = encrypted_message if msg_type == 's' else decrypt(encrypted_message, key, iv)

                if decrypted_message:
                    text_area.config(state=tk.NORMAL)
                    if msg_type == 'p': #message type is private then 
                        text_area.insert(tk.END, decrypted_message + '\n', 'private') #will print in red
                    elif msg_type == 'f': #message was sent by the user
                        text_area.insert(tk.END, decrypted_message + '\n', 'self') #will print in blue
                    else:
                        text_area.insert(tk.END, decrypted_message + '\n') #message sent to everyone and will print in black
                    text_area.config(state=tk.DISABLED)
                    text_area.yview(tk.END)
                else:
                    print("Debug: Decryption failed or message is None")
                    continue

        except Exception as e:
            print(f"Error from {socket1}: {e}")
            socket1.close()
            break

def send_message(sock, choice, message, key, iv):
    try:
        full_message = f"{choice}|{message}|{key}|{iv}" #sends message in format
        print(f"Debug: Sending message: {full_message}")
        sock.send(full_message.encode("utf-8")) 
    except Exception as e:
        print(f"Error sending message: {e}")

def send_file(sock, file_path, recipient):
    try:
        file_size = os.path.getsize(file_path) #the file selected's size is taken
        file_name = os.path.basename(file_path) #file name is taken
        sock.send(f"file|{file_name}|{file_size}|{recipient}".encode("utf-8")) #file name is sent
        with open(file_path, 'rb') as f:
            chunk = f.read() #reads data in file 
            sock.sendall(chunk) #sends all data, if the file data is large then it breaks it into chunks and sends it
        print(f"Debug: File {file_name} sent successfully")
    except Exception as e:
        print(f"Error sending file: {e}")

def encrypt(text):
    key = get_random_bytes(16)  
    iv = get_random_bytes(AES.block_size)

    key_base64 = base64.b64encode(key).decode('utf-8') #to convert Bytes to Character
    iv_base64 = base64.b64encode(iv).decode('utf-8') #to convert Bytes to Character

    data = text.encode('utf-8')
    padded = pad(data, AES.block_size) #pads the data

    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(padded)

    return (
        base64.b64encode(ciphertext).decode('utf-8'),
        key_base64,
        iv_base64
    )

def decrypt(ciphertext, key, iv):
    key = base64.b64decode(key) #converts character to Byte
    iv = base64.b64decode(iv) #converts character to Byte
    ciphertext = base64.b64decode(ciphertext) #converts character to Byte

    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = cipher.decrypt(ciphertext)

    try:
        text = unpad(padded, AES.block_size)
    except ValueError:
        print("Incorrect padding")
        return None

    return text.decode('utf-8')

def main():
    global last_recipient #makes last_recipient as a global variable to be accessed

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('172.22.138.170', 54321))

    root = tk.Tk()
    root.title("Chat Application")

    while(True):
        nickname = simpledialog.askstring("Nickname", "Enter your nickname:") #pop up dialouge to enter nickname
        client_socket.send(nickname.encode("utf-8"))
        req = client_socket.recv(1024).decode("utf-8")
        print(req)  
        if(req == "accepted"): #if server sends that the nickname is accepted then it will open the chat, else it will continue asking for nickname
            break

    root.title(f"Chat Application - {nickname}")

    frame = tk.Frame(root)
    frame.grid(row=0, column=0, sticky="nsew")

    text_area = scrolledtext.ScrolledText(frame, wrap=tk.WORD, state=tk.DISABLED)
    text_area.grid(row=0, column=0, padx=20, pady=5, sticky="nsew")

    text_area.tag_configure('self', foreground='darkblue')
    text_area.tag_configure('private', foreground='red')
    text_area.tag_configure('system', foreground='darkgreen')
    text_area.tag_configure('file', foreground='purple')

    bottom_frame = tk.Frame(root)
    bottom_frame.grid(row=1, column=0, sticky="ew")

    message_entry = tk.Entry(bottom_frame, width=50)
    message_entry.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

    nicknames = []  
    selected_option = tk.StringVar(value=last_recipient) #the nickname that displays in the drop_down box
    combobox = ttk.Combobox(bottom_frame, textvariable=selected_option, values=nicknames) #drop_down box
    combobox.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

    display_last_messages(text_area, nickname)
    def on_send():
        global last_recipient

        message = message_entry.get()
        message = f"{nickname}:{message}"
        choice = combobox.current()
        last_recipient = combobox.get() 

        e_message, key, iv = encrypt(message)

        if message.lower() == "close":
            send_message(client_socket, choice, e_message, key, iv)
            root.quit()
        else:
            send_message(client_socket, choice, e_message, key, iv)
            message_entry.delete(0, tk.END)

    def on_send_file():
        global last_recipient

        file_path = filedialog.askopenfilename()
        if file_path:
            choice = combobox.current()  
            last_recipient = combobox.get()  
            send_file(client_socket, file_path, choice)  

    def help1():
        e_help, key, iv = encrypt("/help")
        send_message(client_socket, "2018", e_help, key, iv)
    
    def log_out():
        e_help, key, iv = encrypt("close")
        send_message(client_socket, "911", "close", key, iv)

    send_button = tk.Button(bottom_frame, text="Send", command=on_send)
    send_button.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

    file_button = tk.Button(bottom_frame, text="Send File", command=on_send_file)
    file_button.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

    help_button = tk.Button(bottom_frame, text="Help", command=help1)
    help_button.grid(row=1, column=2, padx=10, pady=5, sticky="ew")

    corner_button = tk.Button(root, text="Log-Out", command=lambda: (log_out(), client_socket.close(), root.quit()))
    corner_button.grid(row=0, column=1, padx=10, pady=10, sticky="ne")

    root.grid_rowconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=0)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=0)

    threading.Thread(target=handle, args=(client_socket, text_area, combobox, nickname), daemon=True).start() #daemon threading to close the thread automatically when the chat application closes.

    root.mainloop()

if __name__ == '__main__':
    main()
