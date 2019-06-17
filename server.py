keyboard_port = '8334'
mouse_port = '8335'

import zmq
import time
import queue
import pickle
import threading
import pyautogui
import keyboard as kb
from pynput import mouse
from pynput.mouse import Button


def kb_server():
    global keyboard_port
    q = queue.Queue()
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind('tcp://*:'+keyboard_port)
    kb.start_recording(q)
    while True:
        a = q.get()
        key_code = a.scan_code
        name = a.name
        event_type = a.event_type
        message = pickle.dumps(a)
        print(a, key_code, name, event_type)
        socket.send(message)
        print('Send keyboard', message)

def on_click(x, y, button, pressed, socket):
    print('{} at {}'.format('Pressed' if pressed else 'Released', (x, y)))
    screen_width, screen_height = pyautogui.size()
    if button == Button.left:
        button = 'left'
    elif button == Button.right:
        button = 'right'
    elif button == Button.middle:
        button = 'middle'
    else:
        button = 'unknown'
    message = pickle.dumps(('click', x, y, screen_width, screen_height, button, pressed))
    socket.send(message)
    print('Send mouse click', message)

def on_move(x, y, socket):
    global move_time
    if time.time() - move_time < 0.05:
        return True
    move_time = time.time()
    print('move to {}'.format((x, y)))
    screen_width, screen_height = pyautogui.size()
    message = pickle.dumps(('move', x, y, screen_width, screen_height))
    socket.send(message)
    print('Send mouse move', message)

def on_scroll(x, y, dx, dy, socket):
    print('scroll {} at {}'.format('down' if dy < 0 else 'up', (x, y)))
    screen_width, screen_height = pyautogui.size()
    message = pickle.dumps(('scroll', x, y, screen_width, screen_height, dx, dy))
    socket.send(message)
    print('Send mouse scroll', message)

def mouse_server():
    global mouse_port, move_time
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind('tcp://*:'+mouse_port)
    move_time = time.time()
    listener = mouse.Listener(
        on_move=lambda x,y:on_move(x,y,socket),
        on_click=lambda x,y,button,pressed:on_click(x,y,button,pressed,socket),
        on_scroll=lambda x,y,dx,dy:on_scroll(x,y,dx,dy,socket),
    )
    listener.daemon = True
    listener.start()
    listener.join()


if __name__ == "__main__":
    server_list = [kb_server, mouse_server]
    args_list = [(), ()]
    if len(server_list) != len(args_list):
        raise Exception("missing args for server")
    thread_list = []
    try:
        for i in range(len(server_list)):
            server = server_list[i]
            args = args_list[i]
            thread = threading.Thread(target=server, args=args)
            thread.daemon = True
            thread_list.append(thread)

        for thread in thread_list:
            thread.start()
        print("Server start")
        for thread in thread_list:
            thread.join()
    except KeyboardInterrupt:
        print('exit')

