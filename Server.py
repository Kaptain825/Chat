import socket
import threading
import cx_Oracle

# Database connection setup
dsn = "localhost:1521/XE"
user = "system"
password = "mithun12"

lock = threading.Lock()
nicknames = []
sockets = []

def check_nickname_in_db(nickname):
    """Check if the nickname is in the database and return its status."""
    try:
        connection = cx_Oracle.connect(user, password, dsn)
        cursor = connection.cursor()
        cursor.execute("SELECT status FROM users WHERE nickname = :nickname", {"nickname": nickname})
        result = cursor.fetchone()
        return result[0] if result else None
    except cx_Oracle.DatabaseError as e:
        print(f"Database error: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def update_nickname_status(nickname, status):
    """Update the nickname status in the database."""
    try:
        connection = cx_Oracle.connect(user, password, dsn)
        cursor = connection.cursor()
        cursor.execute("UPDATE users SET status = :status WHERE nickname = :nickname", {"status": status, "nickname": nickname})
        connection.commit()
    except cx_Oracle.DatabaseError as e:
        print(f"Database error: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def insert_nickname(nickname):
    """Insert a new nickname into the database."""
    try:
        connection = cx_Oracle.connect(user, password, dsn)
        cursor = connection.cursor()
        cursor.execute("INSERT INTO users (nickname, status) VALUES (:nickname, 'Online')", {"nickname": nickname})
        connection.commit()
    except cx_Oracle.DatabaseError as e:
        print(f"Database error: {e}")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

def handle(client_socket, nicknames, sockets):
    try:
        while True:
            full_message = client_socket.recv(1024).decode('utf-8')
            print(full_message)

            # Check if the message is a file transfer
            if full_message.startswith('file|'):
                parts = full_message.split('|')
                if len(parts) != 4:
                    continue
                file_name = parts[1]
                file_size = int(parts[2])
                recipient_index = int(parts[3])
                file_content = b''

                # Receive the file content
                while len(file_content) < file_size:
                    file_content += client_socket.recv(min(file_size - len(file_content), 1024))

                # Send the file to the specified recipient
                if 0 <= recipient_index < len(sockets):
                    recipient_socket = sockets[recipient_index]
                    recipient_socket.send(f"file|{file_name}|{file_size}".encode('utf-8'))
                    recipient_socket.send(file_content)
                else:
                    # Broadcast the file if recipient index is invalid
                    broad(f"file|{file_name}|{file_size}".encode('utf-8'), sockets)
                    broad(file_content, sockets)

            else:
                parts = full_message.split('|')
                if len(parts) != 4:
                    continue  # Skip if parts are incorrect
                choice, message, key, iv = parts
                print(choice, message, key, iv)

                # Determine how to send the message
                if choice.isdigit():
                    choice = int(choice)
                    if 0 <= choice < len(sockets):
                        receiver = sockets[choice]
                        receiver.send(f"p|{message}|{key}|{iv}".encode('utf-8'))
                        client_socket.send(f"f|{message}|{key}|{iv}".encode('utf-8'))
                    elif choice == len(sockets):  # Broadcast to all clients
                        broad(f"a|{message}|{key}|{iv}".encode('utf-8'), sockets)
                    elif choice == 2018:  # Request for user list
                        txt = "s|"
                        for i, name in enumerate(nicknames):
                            txt += f"{i}:{name} "
                        txt += f"{len(nicknames)}:Everyone|0|0"
                        client_socket.send(txt.encode('utf-8'))
                    elif choice == 911:
                        i = sockets.index(client_socket)
                        del nicknames[i]
                        del sockets[i]
                        update_nickname_status(nicknames[i], 'Offline')  # Update the status to Offline
                        client_socket.close()
                        print(f"{nicknames[i]} has disconnected.")
                    else:
                        break  # Invalid choice
    except Exception as e:
        print("Error: ", e)
    finally:
        # Cleanup on client disconnect
        with lock:
            i = sockets.index(client_socket)
            del nicknames[i]
            del sockets[i]
            update_nickname_status(nicknames[i], 'Offline')  # Update the status to Offline
            client_socket.close()
            print(f"{nicknames[i]} has disconnected.")

def broad(message, sockets):
    """Broadcast a message to all connected sockets."""
    with lock:
        for sock in sockets:
            try:
                sock.send(message)
            except Exception as e:
                print("Error sending message:", e)

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

        # Receive the nickname from the client
        while True:
            nick = client_socket.recv(1024).decode('utf-8')
            status = check_nickname_in_db(nick)

            if status == 'Online':
                client_socket.send("Nickname is already in use. Please enter a new one.".encode('utf-8'))
            else:
                if status == 'Offline':
                    update_nickname_status(nick, 'Online')  # Update to Online
                    client_socket.send("accepted".encode('utf-8'))
                else:
                    insert_nickname(nick)  # Insert new nickname
                    client_socket.send("accepted".encode('utf-8'))

                with lock:
                    nicknames.append(nick)
                    sockets.append(client_socket)

                break

        # Start a new thread to handle the client
        t1 = threading.Thread(target=handle, args=(client_socket, nicknames, sockets))
        t1.start()

if __name__ == "__main__":
    main()
