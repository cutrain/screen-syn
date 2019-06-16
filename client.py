server = '127.0.0.1'
keyboard_port = '8334'
mouse_port = '8335'

import zmq
import pickle
import threading
import pyautogui
import keyboard as kb
from keyboard._keyboard_event import KEY_DOWN, KEY_UP
from pynput import mouse

def kb_client():
    global server, keyboard_port
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect('tcp://'+server+':'+keyboard_port)
    socket.setsockopt(zmq.SUBSCRIBE, b'')
    while True:
        data = socket.recv()
        event = pickle.loads(data)
        key = event.scan_code or event.name
        kb.press(key) if event.event_type == KEY_DOWN else kb.release(key)

def solve_mouse(event, mouse_control):
    type_ = event[0]
    x = event[1]
    y = event[2]
    xx = event[3]
    yy = event[4]
    screen_width, screen_height = pyautogui.size()
    realx = x * screen_width // xx
    realy = y * screen_height // yy
    mouse_control.position = (realx, realy)
    print('mouse at', realx, realy)
    if type_ == 'move':
        print('mouse move only')
    elif type_ == 'click':
        button = event[5]
        pressed = event[6]
        if pressed:
            mouse_control.press(button)
            print('mouse press', button)
        else:
            mouse_control.release(button)
            print('mouse release', button)
    elif type_ == 'scroll':
        dx = event[5]
        dy = event[6]
        mouse_control.scroll(dx, dy)
        print('mouse scroll {},{}'.format(dx, dy))
    else:
        raise Exception("Unknown mouse event "+event[0])

def mouse_client():
    global server, mouse_port
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect('tcp://'+server+':'+mouse_port)
    socket.setsockopt(zmq.SUBSCRIBE, b'')
    mouse_control = mouse.Controller()
    while True:
        data = socket.recv()
        event = pickle.loads(data)
        solve_mouse(event, mouse_control)

if __name__ == '__main__':
    client_list = [kb_client, mouse_client]
    args_list = [(), ()]
    if len(client_list) != len(args_list):
        raise Exception("missing args for client")
    thread_list = []
    try:
        for i in range(len(client_list)):
            client = client_list[i]
            args = args_list[i]
            thread = threading.Thread(target=client, args=args)
            thread.daemon = True
            thread_list.append(thread)

        for thread in thread_list:
            thread.start()
        print("Server start")
        for thread in thread_list:
            thread.join()
    except KeyboardInterrupt:
        print('exit')

