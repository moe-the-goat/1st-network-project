import socket
import threading
import queue

message_queue = queue.Queue() # queue for messages from server

def listen_to_server(client_socket):
    """Listen for messages from the server."""
    while True:
        try:
            message, _ = client_socket.recvfrom(1024)
            print("\n" + message.decode())
            message_queue.put(message.decode())  # Add the message to the queue
        except:
            print("\nConnection gone wrong!!")
            break
        
def display_messages():
    """Continuously display messages from the server and prompt for answers."""
    while not message_queue.empty():
        message = message_queue.get()

        if message.startswith("Question"):  # Check if the message is a question
            answer = input(" Your answer (or type exit to quit): ")  # Get the user's answer
            if answer.lower() == "exit":
                print("Exiting the Trivia Game . . .")
                break
            return answer  # Return the answer to be sent to the server

    return None  # If no question, return None


def trivia_client():
    SERVER_HOST = input("Enter the server IP address : ")
    
    while True:
        SERVER_PORT = int(input("Enter the server's port number: "))
        try:
            if SERVER_PORT == 5689:
                break
            
        except ValueError:
            print("Invalid port number please enter a valid integer")
        
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        username = input("Enter your username: ")
        client_socket.sendto(username.encode(), (SERVER_HOST, SERVER_PORT))

        listener_thread = threading.Thread(target=listen_to_server, args=(client_socket,), daemon=True)
        listener_thread.start()
        
        display_thread = threading.Thread(target=display_messages, daemon=True)
        display_thread.start()

        while True:
            try:
                answer = display_messages()  # Get the user's answer from display_messages

                if answer:
                    client_socket.sendto(answer.encode(), (SERVER_HOST, SERVER_PORT))  # Send answer to server

            except KeyboardInterrupt:
                print("\nExiting the trivia game...")
                break
            except socket.error as e:
                print(f"connection error occurred: {e}")
                break
            
if __name__ == "__main__":
    trivia_client()
