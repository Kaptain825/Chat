import socket
import threading
import cx_Oracle

db_connection = None
db_cursor = None
lock = threading.Lock()
sockets = []
nicknames = []

def connect_to_database():
    global db_connection, db_cursor
    try:
        dsn = "localhost:1521/XE" 
        db_connection = cx_Oracle.connect(
            user="system",
            password="mithun12",
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

def insert_or_update_nickname(nickname):
    try:
        if nickname_exists(nickname):
            db_cursor.execute("UPDATE users SET status = 'online' WHERE nickname = :1", (nickname,))
        else:
            db_cursor.execute("INSERT INTO users (nickname, status) VALUES (:1, 'online')", (nickname,))
        db_connection.commit()
    except cx_Oracle.DatabaseError as e:
        print("Database error during insert/update:", e)
        db_connection.rollback()

def nickname_exists(nickname):
    try:
        db_cursor.execute("SELECT COUNT(*) FROM users WHERE nickname = :1", (nickname,))
        count = db_cursor.fetchone()[0]
        return count > 0
    except cx_Oracle.DatabaseError as e:
        print("Database error during select:", e)
        return False

def get_nicknames():
    try:
        db_cursor.execute("SELECT nickname FROM users WHERE status = 'online'")
        return [row[0] for row in db_cursor.fetchall()]
    except cx_Oracle.DatabaseError as e:
        print("Database error during select:", e)
        return []

def handle(client_socket, sockets):
    try:
        while True:
            full_message = client_socket.recv(1024).decode('utf-8')
            if not full_message:
                break
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
                    broadcast_file(f"file|{file_name}|{file_size}".encode('utf-8'), sockets)
                    broadcast_file(file_content, sockets)
            else:
                parts = full_message.split('|')
                if len(parts) != 4:
                    continue
                choice, message, key, iv = parts
                
                if choice.isdigit():
                    choice = int(choice)
                    if 0 <= choice < len(sockets):
                        receiver = sockets[choice]
                        receiver.send(f"p|{message}|{key}|{iv}".encode('utf-8'))
                        client_socket.send(f"f|{message}|{key}|{iv}".encode('utf-8'))
                    elif choice == len(sockets):
                        broadcast_message(f"a|{message}|{key}|{iv}".encode('utf-8'), sockets)
                    elif choice == 2018:
                        y = len(sockets)
                        nicknames = get_nicknames()
                        txt = "s|"
                        for i, x in enumerate(nicknames):
                            txt += f"{i}:{x}|"
                        txt += f"{len(nicknames)}:Everyone|{y}"
                        client_socket.send(txt.encode('utf-8'))
                    else:
                        break
    except Exception as e:
        print("Error:", e)
    finally:
        with lock:
            if client_socket in sockets:
                i = sockets.index(client_socket)
                nickname = nicknames[i]
                del nicknames[i]
                del sockets[i]
                client_socket.close()
                remove_nickname_from_database(nickname)

def broadcast_message(message, sockets):
    with lock:
        for sock in sockets:
            sock.send(message)

def broadcast_file(message, sockets):
    with lock:
        for sock in sockets:
            sock.send(message)

def remove_nickname_from_database(nickname):
    try:
        db_cursor.execute("UPDATE users SET status = 'offline' WHERE nickname = :1", (nickname,))
        db_connection.commit()
    except cx_Oracle.DatabaseError as e:
        print("Database error during update:", e)
        db_connection.rollback()

def main():
    connect_to_database()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostbyname(socket.gethostname())
    port = 54321
    server_socket.bind((host, port))
    server_socket.listen()

    try:
        while True:
            client_socket, address = server_socket.accept()
            print(f"Connected with {address}")

            client_socket.send("NICK".encode('utf-8'))
            nickname = client_socket.recv(1024).decode('utf-8')

            with lock:
                if nickname in nicknames:
                    # Update existing user's status to 'online'
                    insert_or_update_nickname(nickname)
                    print(f"Nickname {nickname} already in use. Updated to online.")
                else:
                    # Add new nickname
                    insert_or_update_nickname(nickname)
                    nicknames.append(nickname)
                    sockets.append(client_socket)
                    print(f"Nickname {nickname} added to the database")

            client_thread = threading.Thread(target=handle, args=(client_socket, sockets))
            client_thread.start()
    except KeyboardInterrupt:
        print("Shutting down server.")
    finally:
        close_database_connection()
        server_socket.close()

if __name__ == "__main__":
    main()
