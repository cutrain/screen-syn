import os
import zmq
import time
import win32api
import win32gui
import win32ui
import pickle
import logging
import threading
import pyautogui
from pynput import mouse, keyboard as kb
from pynput.mouse import Button
from pynput.keyboard import Key

mainpath = os.path.split(os.path.realpath(__file__))[0]
os.chdir(mainpath)

config_filename = 'server_config.txt'

monitor_keyboard = True
monitor_mouse = True
keyboard_port = '8334'
mouse_port = '8335'
appname = []
log_level = 'info'
interval = 0.03

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
    global config_filename, monitor_keyboard, monitor_mouse, keyboard_port, mouse_port, appname, log_level, interval
    logger.info('start load config')
    try:
        with open(config_filename, 'r') as f:
            data = f.readlines()
    except Exception as e:
        printlog(logger.warning, "load config file error, using default")
        data = []
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
        if config[0] == 'monitor_keyboard':
            if config[1] == '0':
                monitor_keyboard = False
                printlog(logger.info, 'load keyboard off')
            elif config[1] == '1':
                printlog(logger.info, 'load keyboard on')
            else:
                printlog(logger.warning, 'get wrong keyboard value {}'.format(config[1]))
        elif config[0] == 'monitor_mouse':
            if config[1] == '0':
                monitor_mouse = False
                printlog(logger.info, 'load mouse off')
            elif config[1] == '1':
                printlog(logger.info, 'load mouse on')
            else:
                printlog(logger.warning, 'get wrong mouse value {}'.format(config[1]))
        elif config[0] == 'keyboard_port':
            keyboard_port = config[1]
            printlog(logger.info, 'set keyboard port {}'.format(config[1]))
        elif config[0] == 'mouse_port':
            mouse_port = config[1]
            printlog(logger.info, 'set mouse port {}'.format(config[1]))
        elif config[0] == 'appname':
            appname.append(config[1])
            printlog(logger.info, 'append monitoring application name : {}'.format(config[1]))
        elif config[0] == 'log_level':
            config[1] = config[1].lower()
            if config[1] in ['info', 'debug', 'warn', 'warning', 'error']:
                log_level = config[1]
                printlog(logger.info, 'set log level {}'.format(config[1]))
            else:
                printlog(logger.warning, 'unknown log level {}'.format(config[1]))
        elif config[0] == 'interval':
            interval = float(config[1])
            printlog(logger.info, 'set mouse move interval {}'.format(interval))
        else:
            print('unknown config name {} found, ignored'.format(config[0]))
            logger.warning('unknown config name {} found, ignored'.format(config[0]))

    logger.info('finish load config')
    printlog(logger.info, '-'*100)
    printlog(logger.info, 'keyboard: {}'.format('on' if monitor_keyboard else 'off'))
    printlog(logger.info, 'mouse: {}'.format('on' if monitor_mouse else 'off'))
    printlog(logger.info, 'keyboard port: {}'.format(keyboard_port))
    printlog(logger.info, 'mouse port: {}'.format(mouse_port))
    printlog(logger.info, 'application: {}'.format(','.join(appname)))
    printlog(logger.info, 'log level: {}'.format(log_level))
    printlog(logger.info, 'mouse move interval {}'.format(interval))


def check_foreground():
    global appname
    if len(appname) == 0:
        return True
    try:
        now = win32ui.GetForegroundWindow()
        while True:
            nex = now.GetParent()
            if nex is None:
                break
            now = nex
        text = now.GetWindowText()
        logger.debug('get foreground text {}'.format(text))
        for i in appname:
            if text.find(i) != -1:
                return True
        return False
    except win32ui.error as e:
        logging.debug(e)
        return False

def socket_send(message, socket):
    if check_foreground():
        logger.debug('accept send message')
        socket.send(message)
    else:
        logger.debug('reject send message')

def on_press(key, socket):
    try:
        logger.debug('alphanumeric key {} pressed'.format(key.char))
        message = pickle.dumps(('press', 'normal', key.char))
        socket_send(message, socket)
    except AttributeError:
        logger.debug('special key {} pressed'.format(key))
        message = pickle.dumps(('press', 'special', key))
        socket_send(message, socket)

def on_release(key, socket):
    try:
        logger.debug('alphanumeric key {} release'.format(key.char))
        message = pickle.dumps(('release', 'normal', key.char))
        socket_send(message, socket)
    except AttributeError:
        logger.debug('special key {} release'.format(key))
        message = pickle.dumps(('release', 'special', key))
        socket_send(message, socket)


def kb_server():
    global keyboard_port
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind('tcp://*:'+keyboard_port)
    listener = kb.Listener(
        on_press=lambda key:on_press(key, socket),
        on_release=lambda key:on_release(key, socket),
    )
    listener.daemon = True
    listener.start()
    listener.join()


def on_click(x, y, button, pressed, socket):
    logger.debug('{} at {}'.format('Pressed' if pressed else 'Released', (x, y)))
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
    socket_send(message, socket)
    logger.debug('Send mouse click' + str(message))

def on_move(x, y, socket):
    global move_time, interval
    if time.time() - move_time < interval:
        return True
    move_time = time.time()
    logger.debug('move to {}'.format((x, y)))
    screen_width, screen_height = pyautogui.size()
    message = pickle.dumps(('move', x, y, screen_width, screen_height))
    socket_send(message, socket)
    logger.debug('Send mouse move' + str(message))

def on_scroll(x, y, dx, dy, socket):
    logger.debug('scroll {} at {}'.format('down' if dy < 0 else 'up', (x, y)))
    screen_width, screen_height = pyautogui.size()
    message = pickle.dumps(('scroll', x, y, screen_width, screen_height, dx, dy))
    socket_send(message, socket)
    logger.debug('Send mouse scroll' + str(message))

def mouse_server():
    global mouse_port, move_time
    try:
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
    except Exception as e:
        logger.exception(e)

def ping(address):
    return not os.system('ping %s -n 1' % (address,))

if __name__ == "__main__":
    if not ping('ping.cutrain.top'):
        printlog(logger.error, "can not connect to network")
        exit(0)

    try:
        load_config()
    except Exception as e:
        logger.exception(e)
    if log_level == 'debug':
        logger.setLevel(logging.DEBUG)
    elif log_level == 'warn' or log_level == 'warning':
        logger.setLevel(logging.WARNING)
    elif log_level == 'error':
        logger.setLevel(logging.ERROR)
    server_list = []
    args_list = []
    if monitor_keyboard:
        server_list.append(kb_server)
        args_list.append(())
    if monitor_mouse:
        server_list.append(mouse_server)
        args_list.append(())
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
        logger.info("Server start")
        print("Server start")
        for thread in thread_list:
            thread.join()
    except KeyboardInterrupt:
        logger.info('Keyboard Interrupt Exit')
    except Exception as e:
        logger.exception(e)


