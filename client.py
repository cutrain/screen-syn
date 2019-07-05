import os
import zmq
import time
import pickle
import threading
import logging
import pyautogui
from pynput import mouse, keyboard as kb
from pynput.mouse import Button
from pynput.keyboard import Key

mainpath = os.path.split(os.path.realpath(__file__))[0]
os.chdir(mainpath)

config_filename = 'client_config.txt'

server = None
keyboard_port = '8334'
mouse_port = '8335'
log_level = 'info'


logging.basicConfig(
    level=logging.INFO,
    filename='output.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(module)s - %(message)s',
)
logger = logging.getLogger(__name__)


def printlog(logfunc, s):
    print(s)
    logfunc(s)

def load_config():
    global config_filename, server, keyboard_port, mouse_port, log_level
    logger.info('start load config')
    try:
        with open(config_filename, 'r') as f:
            data = f.readlines()
    except Exception as e:
        printlog(logger.warning, "load config file error, exit.")
        exit(0)
    for line in data:
        config = line.strip()
        config = config.split('#')[0]
        if config.find('=') == -1:
            continue
        config = config.split('=')
        config = list(map(lambda x:x.strip(), config))
        if config[1] == '':
            printlog(logger.warning, 'get empty value for {}, ignored'.format(config[0]))
            continue
        if config[0] == 'keyboard_port':
            keyboard_port = config[1]
            printlog(logger.info, 'set keyboard port {}'.format(config[1]))
        elif config[0] == 'mouse_port':
            mouse_port = config[1]
            printlog(logger.info, 'set mouse port {}'.format(config[1]))
        elif config[0] == 'log_level':
            config[1] = config[1].lower()
            if config[1] in ['info', 'debug', 'warn', 'warning', 'error']:
                log_level = config[1]
                printlog(logger.info, 'set log level {}'.format(config[1]))
            else:
                printlog(logger.warning, 'unknown log level {}'.format(config[1]))
        elif config[0] == 'server_ip':
            server = config[1]
            printlog(logger.info, 'set server ip: {}'.format(server))
        else:
            print('unknown config name {} found, ignored'.format(config[0]))
            logger.warning('unknown config name {} found, ignored'.format(config[0]))

    logger.info('finish load config')
    printlog(logger.info, '-'*100)
    printlog(logger.info, 'keyboard port: {}'.format(keyboard_port))
    printlog(logger.info, 'mouse port: {}'.format(mouse_port))
    printlog(logger.info, 'log level: {}'.format(log_level))
    printlog(logger.info, 'server ip: {}'.format(server))


def solve_keyboard(event, kb_control):
    type_ = event[0]
    key_type = event[1]
    key = event[2]
    if key_type == 'normal':
        key = key
    elif key_type == 'special':
        key = Key[key]
    else:
        raise Exception("Unknown keyboard event, key type " + key_type)

    if type_ == 'press':
        kb_control.press(key)
    elif type_ == 'release':
        kb_control.release(key)
    else:
        raise Exception("Unknown keyboard event, press type " + type_)

def kb_client():
    global server, keyboard_port
    try:
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect('tcp://'+server+':'+keyboard_port)
        socket.setsockopt(zmq.SUBSCRIBE, b'')
        kb_control = kb.Controller()
        while True:
            data = socket.recv()
            event = pickle.loads(data)
            if event == 'keyboard pulse':
                printlog(logger.info, 'keyboard server alive')
                continue
            solve_keyboard(event, kb_control)
    except Exception as e:
        logger.exception(e)

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
    logger.debug('mouse at {} {}'.format(realx, realy))
    if type_ == 'move':
        logger.debug('mouse move only')
    elif type_ == 'click':
        button = event[5]
        if button == 'left':
            button = Button.left
        elif button == 'right':
            button = Button.right
        elif button == 'middle':
            button = Button.middle
        else:
            button = Button.unknown
        pressed = event[6]
        if pressed:
            mouse_control.press(button)
            logger.debug('mouse press {}'.format(button))
        else:
            mouse_control.release(button)
            logger.debug('mouse release {}'.format(button))
    elif type_ == 'scroll':
        dx = event[5]
        dy = event[6]
        mouse_control.scroll(dx, dy)
        logger.debug('mouse scroll {},{}'.format(dx, dy))
    else:
        raise Exception("Unknown mouse event "+event[0])

def mouse_client():
    global server, mouse_port
    try:
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect('tcp://'+server+':'+mouse_port)
        socket.setsockopt(zmq.SUBSCRIBE, b'')
        mouse_control = mouse.Controller()
        while True:
            data = socket.recv()
            event = pickle.loads(data)
            if event == 'mouse pulse':
                printlog(logger.info, 'mouse server alive')
                continue
            solve_mouse(event, mouse_control)
    except Exception as e:
        logger.exception(e)

if __name__ == '__main__':
    try:
        load_config()
    except Exception as e:
        logger.exception(e)
    if server is None:
        printlog(logger.error, "server host not set, please set your server ip")
        exit(0)
    if log_level == 'debug':
        logger.setLevel(logging.DEBUG)
    elif log_level == 'warn' or log_level == 'warning':
        logger.setLevel(logging.WARNING)
    elif log_level == 'error':
        logger.setLevel(logging.ERROR)
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
        printlog(logger.info, "Server start")
        for thread in thread_list:
            thread.join()
    except KeyboardInterrupt:
        logger.info('Keyboard Interrupt Exit')
    except Exception as e:
        logger.exception(e)

