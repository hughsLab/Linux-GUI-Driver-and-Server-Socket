import queue
import tkinter as tk
from tkinter import ttk
from math import pi, cos, sin
from modID_1 import check_modID, read_input_registers
  # Importing the data retrieval function
import os
import threading
import time


class Gauge(tk.Canvas):
    def __init__(self, parent, min_value=0, max_value=100, value=50, size=800, label='(V)', **kwargs):
        super(Gauge, self).__init__(parent, width=size, height=size, bg="black", **kwargs)
        self.min_value = min_value
        self.max_value = max_value
        self.value = value
        self.size = size
        self.radius = size // 2
        self.center = (self.radius, self.radius)
        self.arc_extent = 180  # Gauge covers half-circle
        self.label = label
        self.draw_gauge()

    def draw_gauge(self):
        self.delete("all")  # Clear the canvas
        start_angle = 180  # Start from left side
        end_angle = start_angle - self.arc_extent

        # Draw the outer arc
        self.create_arc(
            10, 10, self.size - 10, self.size - 10,
            start=start_angle,
            extent=-self.arc_extent,
            style=tk.ARC,
            outline="white",
            width=4,
        )

        # Draw ticks and labels
        tick_count = 10
        for i in range(tick_count + 1):
            angle = start_angle - (i * self.arc_extent / tick_count)
            self.draw_tick(angle, i * (self.max_value - self.min_value) / tick_count)

        # Draw the needle
        self.draw_needle()

        # Draw label
        self.create_text(self.center[0], self.size - 30, text=self.label, font=("Arial", 16, "bold"), fill="red")

    def draw_tick(self, angle, value):
        rad = pi * angle / 180
        inner_length = self.radius - 30
        outer_length = self.radius - 10
        x1 = self.center[0] + inner_length * cos(rad)
        y1 = self.center[1] - inner_length * sin(rad)
        x2 = self.center[0] + outer_length * cos(rad)
        y2 = self.center[1] - outer_length * sin(rad)

        self.create_line(x1, y1, x2, y2, fill="white", width=0)
        text_x = self.center[0] + (inner_length - 20) * cos(rad)
        text_y = self.center[1] - (inner_length - 20) * sin(rad)
        self.create_text(text_x, text_y, text=str(int(value)), font=("Arial", 12, "bold"), fill="orange")

    def draw_needle(self):
        needle_angle = 180 - self.arc_extent * ((self.value - self.min_value) / (self.max_value - self.min_value))
        rad = pi * needle_angle / 180
        needle_length = self.radius - 40
        x = self.center[0] + needle_length * cos(rad)
        y = self.center[1] - needle_length * sin(rad)
        self.create_line(self.center[0], self.center[1], x, y, fill="red", width=5)

    def update_value(self, new_value):
        self.value = new_value
        self.draw_gauge()




# Create a queue for sharing data between threads
data_queue = queue.Queue()
# Background thread for Modbus polling
# Background thread for Modbus polling
def poll_modbus():
    max_attempts = 3
    while True:
        modID = check_modID()  # Find a valid Modbus ID
        attempt = 0

        while modID is not None and attempt < max_attempts:
            try:
                # Read input registers
                voltage, temp, current, capacity, modID = read_input_registers(modID)

                # Check if all values are None
                if all(value is None for value in [voltage, temp, current, capacity]):
                    attempt += 1
                    print("Attempt {attempt}: No data received from modID {modID}. Retrying...")
                    continue

                # Put valid data into the queue for GUI updates
                data_queue.put((voltage, temp, current, capacity, modID))
                attempt = 0  # Reset attempts on successful data read
                break

            except Exception as e:
                attempt += 1
                print("Attempt {attempt}: Error reading registers from modID {modID} - {str(e)}")

        # Handle case when all attempts fail
        if attempt >= max_attempts:
            print("Max attempts reached for modID {modID}. Resetting modID...")

            # Push N/A to queue for GUI update
            data_queue.put((None, None, None, None, modID))  

            # Reset modID and continuously check for a valid modID
            while modID is None:
                print("Attempting to find a valid Modbus ID...")
                modID = check_modID()  # Keep checking until a valid modID is found
                time.sleep(1)  # Small delay to avoid overloading the CPU

            print("Found valid modID {modID}. Attempting to read data again...")

        time.sleep(3)  # Poll every 3 seconds


# GUI update function
def update_gui():
    global last_update_time
    try:
        # Check if there is new data in the queue
        if not data_queue.empty():
            voltage, temp, current, capacity, modID = data_queue.get_nowait()

            # Update voltage
            voltage_value.config(text="{:.2f} V".format(voltage) if voltage is not None else "N/A")


            # Update temperature
            temperature_value.config(text="{:.2f} °C".format(temp) if temp is not None else "N/A")
            if temp is not None:
                if temp > 45:
                    control_relay('off')
                

            # Update current
            current_value.config(text="{:.2f} A".format(current) if current is not None else "N/A")

            # Update capacity
            capacity_value.config(text="{:.2f} %".format(capacity) if capacity is not None else "N/A")
            if capacity is not None:
                if capacity >= 93:
                    control_relay('off')
                elif capacity <= 23:
                    control_relay('off')

            # Update voltage gauge
            if voltage is not None:
                voltage_gauge.update_value(voltage)

            # Display modID
            modID_value.config(text="{:.1f}".format(modID) if modID is not None else "N/A")

            # Update the timestamp of the last valid data
            if voltage is not None or temp is not None or current is not None or capacity is not None:
                last_update_time = time.time()

        # Check for timeout (e.g., 15 seconds since the last valid data)
        if last_update_time and (time.time() - last_update_time > 20):
            print("No valid data for 15 seconds. Resetting...")
            data_queue.put((None, None, None, None, None))  # Reset GUI to N/A
            last_update_time = None  # Clear last update time

    except Exception as e:
        print("Error updating GUI:", str(e))

    # Schedule the next GUI update
    root.after(2000, update_gui)  # Update every second




# Start the Modbus polling thread
thread = threading.Thread(target=poll_modbus, daemon=True)
thread.start()




def control_relay(state):
    """
    Control Relay 2.

    :param state: 'on' to turn the relay on, 'off' to turn it off.
    """
    RELAY_2_PATH = "/sys/class/leds/relay-jp2/brightness"
    if state not in ['on', 'off']:
        raise ValueError("Invalid state. Use 'on' or 'off'.")

    value = '1' if state is 'on' else '0'

    try:
        with open(RELAY_2_PATH, 'w') as relay_file:
            relay_file.write(value)
        print("Relay 2 turned {}.".format(state))
    except PermissionError:
        print("Permission denied: Please run the script with appropriate permissions.")
    except FileNotFoundError:
        print("File not found: {}. Ensure the RelayCape is properly connected.".format(RELAY_2_PATH))
    except Exception as e:
        print("An error occurred: {}".format(e))




def control_relay_1(state):
    """
    Control Relay 1.

    :param state: 'on' to turn the relay on, 'off' to turn it off.
    """
    RELAY_1_PATH = "/sys/class/leds/relay-jp1/brightness"
    if state not in ['on', 'off']:
        raise ValueError("Invalid state. Use 'on' or 'off'.")

    value = '1' if state is 'on' else '0'

    try:
        with open(RELAY_1_PATH, 'w') as relay_file:
            relay_file.write(value)
        print("Relay 1 turned {}.".format(state))
    except PermissionError:
        print("Permission denied: Please run the script with appropriate permissions.")
    except FileNotFoundError:
        print("File not found: {}. Ensure the RelayCape is properly connected.".format(RELAY_1_PATH))
    except Exception as e:
        print("An error occurred: {}".format(e))
        








root = tk.Tk()
root.attributes("-fullscreen", True)  # Set full screen on start
root.title("System Details")
root.geometry("800x480")  # Set fixed size for the LCD display.
root.configure(bg="#4a4a4a")
style = ttk.Style()
style.configure("TFrame", background="#4a4a4a")
style.configure("Title.TLabel", font=("Arial", 24, "bold"), background="#4a4a4a", foreground="orange")
style.configure("Data.TLabel", font=("Arial", 24), background="#ffffff", foreground="black", anchor="center")
style.configure("Section.TLabel", font=("Arial", 18), background="#4a4a4a", foreground="orange")

details_frame = ttk.Frame(root, style="TFrame", padding=(30, 0))
details_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")

details_title = ttk.Label(details_frame, text="System Details of Battery: ", style="Title.TLabel")
details_title.grid(row=0, column=0, columnspan=3, padx=(50, 50), pady=(0, 0), sticky="n")


modID_value = ttk.Label(details_frame, text="N/A", style="Data.TLabel", width=12)
modID_value.grid(row=0, column=1, pady=(10, 50), padx=(50, 0), sticky="w", columnspan=3)




# Estimated Capacity
capacity_label = ttk.Label(details_frame, text="Estimated Capacity %", style="Section.TLabel")
capacity_label.grid(row=2, column=2, padx=(50, 0), pady=(30, 80))  # Adjusted position
capacity_value = ttk.Label(details_frame, text="N/A", style="Data.TLabel", width=12)
capacity_value.grid(row=2, column=2, padx=(50, 0), pady=(40, 20))  # Adjusted position

# Current
current_label = ttk.Label(details_frame, text="Current (A)", style="Section.TLabel")
current_label.grid(row=2, column=2, padx=(50, 0), pady=(300, 50))  # Adjusted position
current_value = ttk.Label(details_frame, text="N/A", style="Data.TLabel", width=12)
current_value.grid(row=2, column=2, padx=(50, 0), pady=(350, 35))  # Adjusted position

# Temperature
temperature_label = ttk.Label(details_frame, text="Temperature °C", style="Section.TLabel")
temperature_label.grid(row=2, column=2, padx=(50, 0), pady=(10, 205), sticky="n")  # Adjusted position
temperature_value = ttk.Label(details_frame, text="N/A", style="Data.TLabel", width=12)
temperature_value.grid(row=2, column=2, padx=(50, 0), pady=(40, 375))  # Adjusted position


# Voltage
voltage_gauge = Gauge(details_frame, min_value=0, max_value=100, value=50, size=400, label="(V)")
voltage_gauge.grid(row=2, column=0, padx=(280, 0), pady=(0, 0))  # Adjusted position

voltage_value = ttk.Label(details_frame, text="N/A", style="Data.TLabel", width=12)
voltage_value.grid(row=2, column=0, padx=(290, 20), pady=(80, 0))  # Adjusted position




# Relay 2! With 5 min on & off for heat control
def toggle_relay_charge():
    if toggle_relay_charge.is_shutdown_confirmed:
        if toggle_relay_charge.is_relay_on:
            # Turn the relay off and stop the toggling loop
            control_relay('off')
          #  toggle_button_discharge.config(bg="light blue", activebackground="red", text="Discharge")  # Reset to default
            toggle_button_charge.config(bg="light blue", activebackground="red", text="Charge")  # Reset to default
            toggle_relay_charge.stop_toggling = True  # Signal to stop the loop
        else:
            # Turn the relay on and start the toggling loop
            control_relay('on')
          #  toggle_button_discharge.config(bg="red", activebackground="red", text="ACTIVE")  # Change to red when pressed
            toggle_button_charge.config(bg="red", activebackground="red", text="ACTIVE")  # Change to red when pressed
            toggle_relay_charge.stop_toggling = False  # Allow toggling loop to start
            start_relay_toggle_charge_thread()  # Start the background thread

        toggle_relay_charge.is_relay_on = not toggle_relay_charge.is_relay_on
        toggle_relay_charge.is_shutdown_confirmed = False  # Reset confirmation state
    else:
      #  toggle_button_discharge.config(bg="red", activebackground="dark red", text="Confirm")
        toggle_button_charge.config(bg="red", activebackground="dark red", text="Confirm")
        toggle_relay_charge.is_shutdown_confirmed = True

# Reset the button state if the user doesn't confirm
def reset_discharge_button_charge():
    if toggle_relay_charge.is_shutdown_confirmed:
       # toggle_button_discharge.config(bg="light blue", activebackground="red", text="ACTIVE")
        toggle_button_charge.config(bg="light blue", activebackground="red", text="ACTIVE") 

        
        toggle_relay_charge.is_shutdown_confirmed = False



def toggle_relay():
    if toggle_relay.is_shutdown_confirmed:
        if toggle_relay.is_relay_on:
            # Turn the relay off and stop the toggling loop
            control_relay('off')
            toggle_button_discharge.config(bg="light blue", activebackground="red", text="Discharge")  # Reset to default
         #   toggle_button_charge.config(bg="light blue", activebackground="red", text="Charge")  # Reset to default
            toggle_relay.stop_toggling = True  # Signal to stop the loop
        else:
            # Turn the relay on and start the toggling loop
            control_relay('on')
            toggle_button_discharge.config(bg="red", activebackground="red", text="ACTIVE")  # Change to red when pressed
          #  toggle_button_charge.config(bg="red", activebackground="red", text="ACTIVE")  # Change to red when pressed
            toggle_relay.stop_toggling = False  # Allow toggling loop to start
            start_relay_toggle_thread()  # Start the background thread

        toggle_relay.is_relay_on = not toggle_relay.is_relay_on
        toggle_relay.is_shutdown_confirmed = False  # Reset confirmation state
    else:
        toggle_button_discharge.config(bg="red", activebackground="dark red", text="Confirm")
     #   toggle_button_charge.config(bg="red", activebackground="dark red", text="Confirm")
        toggle_relay.is_shutdown_confirmed = True

# Reset the button state if the user doesn't confirm
def reset_discharge_button():
    if toggle_relay.is_shutdown_confirmed:
        toggle_button_discharge.config(bg="light blue", activebackground="red", text="ACTIVE")
     #   toggle_button_charge.config(bg="light blue", activebackground="red", text="ACTIVE") 

        
        toggle_relay.is_shutdown_confirmed = False


def toggle_relay_charge_loop():
    while not toggle_relay_charge.stop_toggling:  # Continue looping until stop_toggling is True
        control_relay('on')
        print("Relay ON")  # Debugging print
        time.sleep(10800)  # Wait for 5 mins
        if toggle_relay_charge.stop_toggling:  # Check if the loop should stop
            break
        control_relay('off')
        print("Relay OFF")  # Debugging print
        time.sleep(10800)  # Wait for 5 mins

def start_relay_toggle_charge_thread():
    # Start a background thread to handle the toggling loop
    thread = threading.Thread(target=toggle_relay_charge_loop)
    thread.daemon = True  # Ensure the thread exits when the main program exits
    thread.start()

def toggle_relay_loop():
    while not toggle_relay.stop_toggling:  # Continue looping until stop_toggling is True
        control_relay('on')
        print("Relay ON")  # Debugging print
        time.sleep(10800)  # Wait for 5 mins
        if toggle_relay.stop_toggling:  # Check if the loop should stop
            break
        control_relay('off')
        print("Relay OFF")  # Debugging print
        time.sleep(10800)  # Wait for 5 mins

def start_relay_toggle_thread():
    # Start a background thread to handle the toggling loop
    thread = threading.Thread(target=toggle_relay_loop)
    thread.daemon = True  # Ensure the thread exits when the main program exits
    thread.start()

# Initialize variables
toggle_relay.is_relay_on = False
toggle_relay.stop_toggling = True
toggle_relay.is_shutdown_confirmed = False

toggle_relay_charge.is_relay_on = False
toggle_relay_charge.stop_toggling = True
toggle_relay_charge.is_shutdown_confirmed = False



# Create charge button
toggle_button_charge = tk.Button(
    root,
    text="Charge",
    command=toggle_relay_charge,
    font=("Arial", 20, "bold"),  # Larger font size
    bg="light blue",  # Default background color
    fg="black",  # Default text color
    activebackground="red",  # Color when pressed
    activeforeground="white",  # Text color when pressed
    width=18,  # Adjust button width
    height=2  # Adjust button height
)
toggle_button_charge.grid(row=4, column=0, padx=(325, 0), pady=(5, 50))  # Moved down and spaced apart






# Create discharge button
toggle_button_discharge = tk.Button(
    root,
    text="Discharge",
    command=toggle_relay,
    font=("Arial", 20, "bold"),  # Larger font size
    bg="light blue",  # Default background color
    fg="black",  # Default text color
    activebackground="red",  # Color when pressed
    activeforeground="white",  # Text color when pressed
    width=18,  # Adjust button width
    height=2  # Adjust button height
)
toggle_button_discharge.grid(row=4, column=0, padx=(97, 680), pady=(5, 50))  # Moved down and spaced apart

# Add a timer to reset the button state after 5 seconds if not confirmed
root.after(2000, reset_discharge_button)




root.after(3000, update_gui)
root.mainloop()
