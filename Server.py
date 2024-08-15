import socket
import threading
import cx_Oracle

db_connection = None
db_cursor = None
lock = threading.Lock()
sockets = []

def connect_to_database():
    global db_connection, db_cursor
    try:
        dsn = "localhost:1521/XE" 
        db_connection = cx_Oracle.connect(
            user="your_username",
            password="your_password",
            dsn=dsn,
            encoding="UTF-8"
        )
        db_cursor = db_connection.cursor()
    except cx_Oracle.DatabaseError as e:
        print("Database connection error:", e)

def close_database_connection():
    global db_connection, db_cursor
    if db_cursor:
        db_cursor.close()
    if db_connection:
        db_connection.close()

def insert_nickname(nickname):
    try:
        db_cursor.execute("INSERT INTO users (nickname) VALUES (:1)", (nickname,))
        db_connection.commit()
    except cx_Oracle.DatabaseError as e:
        print("Database error during insert:", e)
        db_connection.rollback()

def get_nicknames():
    try:
        db_cursor.execute("SELECT nickname FROM users")
        return [row[0] for row in db_cursor.fetchall()]
    except cx_Oracle.DatabaseError as e:
        print("Database error during retrieval:", e)
        return []
    
def handle(client_socket, sockets):
    try:
        while True:
            full_message = client_socket.recv(1024).decode('utf-8')
            print(full_message)
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
                if len(parts) != 4:
                    continue
                choice, message, key, iv = parts
                print(choice, message, key, iv)
                
                if choice.isdigit():
                    choice = int(choice)
                    if 0 <= choice < len(sockets):
                        receiver = sockets[choice]
                        receiver.send(f"p|{message}|{key}|{iv}".encode('utf-8'))
                        client_socket.send(f"f|{message}|{key}|{iv}".encode('utf-8'))
                    elif choice == len(sockets):
                        broad(f"a|{message}|{key}|{iv}".encode('utf-8'), sockets)
                    elif choice == 2018:
                        nicknames = get_nicknames()
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
        print("Error:", e)
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
    connect_to_database()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostbyname(socket.gethostname())
    port = 54321
    server_socket.bind((host, port))
    server_socket.listen()
    print("Server is listening...")

    try:
        while True:
            client_socket, client_address = server_socket.accept()
            print(f"{client_socket} has connected...")

            nick = client_socket.recv(1024).decode('utf-8')

            with lock:
                sockets.append(client_socket)
                insert_nickname(nick)  

            t1 = threading.Thread(target=handle, args=(client_socket, sockets))
            t1.start()
    finally:
        close_database_connection()  

if __name__ == "__main__":
    main()
