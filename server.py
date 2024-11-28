import socket
import random
import threading
import time


def enqueue_answer(data, addr):
    answer_queue.put((data, addr))

# Server configuration
HOST = "0.0.0.0"
PORT = 5689

# Questions and answers database
questions = [
    ("What is the capital of France?", "Paris"),
    ("What is 2 + 2?", "4"),
    ("What is the color of the sky on a clear day?", "Blue"),
    ("Who wrote 'Romeo and Juliet'?", "Shakespeare"),
    ("What is the longest river in the world?", "Nile"),
    ("What is the capital of Japan?", "Tokyo"),
    ("Which planet is known as the Red Planet?", "Mars"),
    ("What is the smallest country in the world by area?", "Vatican"),
    ("What is the chemical symbol for gold?", "Au"),
    ("What gas do plants absorb from the atmosphere during photosynthesis?", "Carbon"),
]

clients = {}  # Tracks client addresses and scores
lock = threading.Lock()  # Prevents race conditions


def broadcast(message, server_socket):
    """Send a message to all connected clients."""
    with lock:
        for client in clients.keys():
            try:
                server_socket.sendto(message.encode(), client)
            except Exception as e:
                print(f"Failed to send message to {client}: {e}")


def register_new_clients(server_socket, ip):
    """Continuously register new clients while the game is ongoing."""
    global clients
    while True:
        try:
            data, addr = server_socket.recvfrom(1024)
            username = data.decode().strip()
            with lock:
                if addr not in clients:
                    clients[addr] = {"username": username, "score": 0, "answered": False}
                    print(f"{username} joined the game from ({addr})")
                    server_socket.sendto(f"Registered with the Trivia Game server at IP {ip}, Port {PORT}\nWaiting for the game to start".encode(), addr)
                    threading.Thread(target=broadcast, args=(f"{username} has joined the game!\n  Current number of players: {len(clients)}", server_socket), daemon=True).start()

        except socket.timeout:
            continue


def handle_client_answers(server_socket, question, correct_answer):
    """Handle answers for the current question."""
    start_time = time.time()
    first_correct_time = None

    def process_answer(data, addr):
        """Process a single client's answer."""
        nonlocal first_correct_time  # Allow modification of the shared variable
        answer = data.decode().strip()
        with lock:
            if addr not in clients or clients[addr]["answered"]:
                return
            
            clients[addr]["answered"] = True

            server_socket.sendto(f"Answer Submitted: {answer}".encode(), addr)
            if answer.lower() == correct_answer.lower():
                if not first_correct_time:
                    first_correct_time = time.time()
                    clients[addr]["score"] += 10  # Full points for first correct answer
                else:
                    time_diff = time.time() - first_correct_time
                    score_multiplier = max(0.5, 1 - time_diff / 10)  # Decrease score for slower answers
                    clients[addr]["score"] += int(10 * score_multiplier)
                server_socket.sendto("Correct!".encode(), addr)
                print(f"Received answer from {clients[addr]['username']} ({addr}): {answer} - Correct!")
            else:
                server_socket.sendto("Wrong answer.".encode(), addr)
                print(f"Received answer from {clients[addr]['username']} ({addr}): {answer} - Incorrect!")


    while time.time() - start_time < 30:
        try:
            data, addr = server_socket.recvfrom(1024)
            # Start a thread to process this answer
            threading.Thread(target=process_answer, args=(data, addr), daemon=True).start()

            # Exit early if all clients have answered
            with lock:
                if all(client["answered"] for client in clients.values()):
                    break
        except socket.timeout:
            continue
    time.sleep(2)

def game_server():
    """Start the trivia game server."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.settimeout(1)  # Set timeout for non-blocking behavior
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        print(f"Trivia Game server started and listening on ({ip_address}, {PORT})")

        # Start a thread for registering new clients
        threading.Thread(target=register_new_clients, args=(server_socket, ip_address,), daemon=True).start()

        # Initialize "rounds won" tracker
        with lock:
            for client in clients:
                clients[client]["rounds_won"] = 0

        while True:
            # Broadcast start of the game round
            if len(clients) < 2:
                print("Waiting for at least 2 clients to join the game . . .")
                time.sleep(1.5)
                continue
            
            with lock:
                for client in clients:
                    clients[client]["answered"] = False

            print("Starting the Trivia Game Round in 30 seconds! Get Ready!")
            broadcast("Starting the Trivia Game Round in 30 seconds! Get Ready!", server_socket)
            time.sleep(30)

            # Ask 3 random questions per round
            i = 1
            for question, correct_answer in random.sample(questions, 3):
                print(f"Question {i}: {question}")
                broadcast(f"Question {i}: {question}", server_socket)

                # Reset all clients' "answered" status
                with lock:
                    for client in clients:
                        clients[client]["answered"] = False

                handle_client_answers(server_socket, question, correct_answer)
                print("TIME'S UP")
                broadcast(f"TIME'S UP! The correct answer was: {correct_answer}", server_socket)

                # Broadcast scores after each question
                leaderboard = "\n".join(
                    [f"{clients[client]['username']}: {clients[client]['score']} points" for client in clients]
                )
                broadcast(f"Scores after question {i}:\n{leaderboard}", server_socket)

                if i == 3:
                    break

                broadcast("Next question in 60 seconds...", server_socket)
                time.sleep(15)
                i += 1

            # Determine the round winner
            round_winner = max(clients, key=lambda c: clients[c]["score"])  # Client with the highest score
            clients[round_winner]["rounds_won"] += 1  # Increment "rounds won" for the winner
            broadcast(
                f"The winner of this round is {clients[round_winner]['username']} with {clients[round_winner]['score']} points!",
                server_socket,
            )
            print(
                f"Round winner: {clients[round_winner]['username']} with {clients[round_winner]['score']} points"
            )

            # Reset all clients' scores for the next round
            with lock:
                for client in clients:
                    clients[client]["score"] = 0

            # Announce overall scores
            overall_leaderboard = "\n".join(
                [f"{clients[client]['username']}: {clients[client]['rounds_won']} rounds won" for client in clients]
            )
            broadcast(f"Rounds won leaderboard:\n{overall_leaderboard}", server_socket)

            broadcast("New round starting soon! Latecomers can still join.", server_socket)
            time.sleep(15)

            # End game condition (optional, e.g., after a fixed number of rounds)
            # If game is over, announce the overall winner
            overall_winner = max(clients, key=lambda c: clients[c]["rounds_won"])
            broadcast(
                f"GAME OVER! The winner is {clients[overall_winner]['username']} with {clients[overall_winner]['rounds_won']} rounds won! Congratulations!",
                server_socket,
            )
            print(
                f"Trivia Game has ended. Overall winner: {clients[overall_winner]['username']} with {clients[overall_winner]['rounds_won']} rounds won."
            )
            break



if __name__ == "__main__":
    game_server()
