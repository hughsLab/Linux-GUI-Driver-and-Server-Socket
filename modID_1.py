import threading
import time
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
import struct
import socket  # Add socket import

# Initialize Modbus client configuration
client = ModbusClient(method='ascii', port='/dev/ttyUSB0', baudrate=115200, parity='E', stopbits=1, bytesize=7)

# Define register addresses (0-based for pymodbus)
address_voltage = 30001 - 30001
address_temp = 31001 - 30001
address_current = 33003 - 30001
address_capacity = 34001 - 30001

# Shared variables
modID_in_use = None
last_data_time = None
lock = threading.Lock()


def check_modID():
    """
    Check Modbus IDs (1, 2, 3, 4) to find which one has valid data.
    If data is found, return the modID.
    Attempt to reconnect to the USB device if the connection fails.
    """
    global client

    print("Checking Modbus IDs...")
    for modID in [1, 2, 3, 4]:
        print("Attempting to read voltage for modID {modID}...")

        # Check and reconnect if client is not connected
        if not client.connect():
            print("Client connection failed. Reinitializing...")
            client = ModbusClient(method='ascii', port='/dev/ttyUSB0', baudrate=115200, parity='E', stopbits=1, bytesize=7)
            time.sleep(2)  # Small delay to allow reconnection

        # Attempt to read voltage data
        try:
            result_voltage = client.read_input_registers(address_voltage, count=1, unit=modID)
            if not result_voltage.isError() and result_voltage.registers:  # Ensure valid data
                print("Data found for modID {modID}.")
                return modID
            else:
                print("No data for modID {modID}.")
        except Exception as e:
            print("Error while reading modID {modID}: {e}")

    return None  # If no data is found for any modID


def read_input_registers(modID):
    """
    Reads input registers from the battery with the provided modID and returns
    the voltage, temperature, current, relative capacity values, and modID.
    """
    global last_data_time
    try:
        if not client.connect():
            print("Failed to connect to Modbus client.")
            return None, None, None, None, modID

        # Voltage
        result_voltage = client.read_input_registers(address_voltage, count=1, unit=modID)
        voltage_value = round(result_voltage.registers[0] / 1000, 2) if not result_voltage.isError() else None

        # Temperature
        result_temp = client.read_input_registers(address_temp, count=1, unit=modID)
        temp_value = result_temp.registers[0]
        if temp_value > 32767:
            temp_value -= 65536
        temp_value = round(temp_value, 2)

        # Current
        result_current = client.read_input_registers(address_current, count=2, unit=modID)
        if not result_current.isError():
            high, low = result_current.registers
            raw_current_value = (high << 16) | low
            if raw_current_value > 2147483647:
                raw_current_value -= 4294967296
            current_value = round(raw_current_value / 1000.0, 2)
        else:
            current_value = None

        # Relative Capacity
        result_capacity = client.read_input_registers(address_capacity, count=2, unit=modID)
        if not result_capacity.isError():
            high, low = result_capacity.registers
            combined = (high << 16) | low
            capacity_value = round(struct.unpack('!f', struct.pack('!I', combined))[0], 2)
        else:
            capacity_value = None

        # Update last data time if data is valid
        if voltage_value is not None or current_value is not None:
            with lock:
                last_data_time = time.time()

        return voltage_value, temp_value, current_value, capacity_value, modID

    finally:
        client.close()


def send_data(voltage, temp, current, capacity, modID):
    """
    Sends the real data via TCP to the specified receiver IP and port.
    """
   # sender_ip = '172.16.29.53' Kepp the binding open for DHCP
    receiver_ip = '172.16.28.29'
    port = 12345

    # Define the message
    message = "voltage={}, temp={}, current={}, capacity={}, modID={}\n".format(
        round(voltage), round(temp), round(current), round(capacity), modID)
    print("Debug: Message to be sent: {}".format(message))

    # Create a TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   # sock.bind((sender_ip, 0))

    # Attempt to connect the socket to the specified IP address and port
    while True:
        try:
            sock.connect((receiver_ip, port))
            break
        except ConnectionRefusedError:
            print("Debug: Connection refused, retrying in 5 seconds...")
            time.sleep(5)

    # Send the message to the specified port
    sock.sendall(message.encode())
    print("Debug: Message sent: {}".format(message))

    # Close the socket
    sock.close()


def monitor_modbus():
    """
    Continuously monitor the selected modID for new data. If no new data is received
    within 10 seconds, reset to checking all modIDs.
    """
    global modID_in_use, last_data_time

    while True:
        if modID_in_use is not None:
            print("Polling data for modID {modID_in_use}...")
            data = read_input_registers(modID_in_use)

            if data == (None, None, None, None, None):
                print("No new data received. Displaying N/A.")
            else:
                voltage, temp, current, capacity, modID = data
                print("Voltage: {voltage}V, Temp: {temp}°C, Current: {current}A, Capacity: {capacity}%")
                send_data(voltage, temp, current, capacity, modID)  # Send data via TCP

            # Check if 10 seconds have passed since the last data update
            with lock:
                if last_data_time and (time.time() - last_data_time > 15):
                    print("No new data for 10 seconds. Resetting to check all modIDs...")
                    modID_in_use = None  # Reset modID to restart the search
                    last_data_time = None  # Clear last data time to avoid stale data

        # If no modID is in use, search for a valid modID
        if modID_in_use is None:
            modID_in_use = check_modID()
            if modID_in_use:
                print("Found modID {modID_in_use}. Starting to poll data.")
            else:
                print("No valid modID found. Retrying in 5 seconds...")
                time.sleep(5)  # Retry after a delay


# Start monitoring in a separate thread
modbus_thread = threading.Thread(target=monitor_modbus, daemon=True)
modbus_thread.start()

# Initialize system
print("System initialized. Monitoring Modbus devices...")