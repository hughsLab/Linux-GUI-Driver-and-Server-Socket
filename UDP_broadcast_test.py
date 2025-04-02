import socket
import time

# Assign values
voltage = 2
temp = 2
current = 2
capacity = 2
modID = 2

# Define the message
message = f"voltage={voltage:d}, temp={temp:d}, current={current:d}, capacity={capacity:d}, modID={modID:d}\n"
print(f"Debug: Message to be sent: {message}")

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to the specified IP address
#sock.bind(('172.16.29.56', 0))

# Enable broadcasting mode
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

while True:
    # Send the message to the specified port
    sock.sendto(message.encode(), ('<broadcast>', 65534))
    print(f"Debug: Message sent: {message}")
    # Wait for 1 second
    time.sleep(1)

# Close the socket
sock.close()
