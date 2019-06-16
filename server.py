port = '8334'

import zmq
import time
import queue
import pickle
import threading
import pyautogui
import keyboard as kb


def kb_server():
    global port
    q = queue.Queue()
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind('tcp://*:'+port)
    kb.start_recording(q)
    while True:
        a = q.get()
        key_code = a.scan_code
        name = a.name
        event_type = a.event_type
        message = pickle.dumps(a)
        print(a, key_code, name, event_type)
        socket.send(message)
        print('SEND', message)


if __name__ == "__main__":
    server_list = [kb_server]
    args_list = [()]
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

