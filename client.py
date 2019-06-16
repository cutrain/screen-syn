server = '127.0.0.1'
port = '8334'

import zmq
import pickle
import threading
import pyautogui
import keyboard as kb
from keyboard._keyboard_event import KEY_DOWN, KEY_UP

def kb_client():
    global server, port
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.connect('tcp://'+server+':'+port)
    socket.setsocketopt(zmq.SUBSCRIBE, b'')
    while True:
        data = socket.recv()
        event = pickle.loads(data)
        key = event.scan_code or event.name
        kb.press(key) if event.event_type == KEY_DOWN else kb.release(key)


if __name__ == '__main__':
    client_list = [kb_client]
    args_list = [()]
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

