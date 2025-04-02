import socket

def start_tcp_server():
    # Create a TCP/IP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the port
    server_address = ('', 12345)
    server_socket.bind(server_address)

    # Listen for incoming connections
    server_socket.listen(1)
    print("Server is listening on port 12345...")

    while True:
        # Wait for a connection
        connection, client_address = server_socket.accept()
        try:
            print(f"Connection from {client_address}")

            # Receive the data in small chunks and print it
            while True:
                data = connection.recv(1024)
                if data:
                    # Assume data is received in the form of a dictionary
                    data_dict = eval(data.decode())
                    print(f"Received data: {data_dict}")
                else:
                    break
        finally:
            # Clean up the connection
            connection.close()

if __name__ == "__main__":
    start_tcp_server()
