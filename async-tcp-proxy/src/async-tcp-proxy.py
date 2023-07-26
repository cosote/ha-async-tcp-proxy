#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of the ha-async-tcp-proxy project
#
# Copyright (c) 2023 Jens Bornemann
# Based on tcpproxy by René Werner, https://github.com/ickerwx/tcpproxy
#
# Distributed under the Apache 2.0 and MIT license. See LICENSE and LICENSE_MIT for more info.
#

import argparse
import pkgutil
import os
import sys
import signal
import threading
import socket
import socks
import time
import select
import errno
import asyncio
import queue
from datetime import datetime

def is_valid_ip4(ip):
    # some rudimentary checks if ip is actually a valid IP
    octets = ip.split('.')
    if len(octets) != 4:
        return False
    return octets[0] != 0 and all(0 <= int(octet) <= 255 for octet in octets)

def parse_args():
    parser = argparse.ArgumentParser(description='Simple TCP proxy for data ' +
                                                 'interception and ' +
                                                 'modification. ' +
                                                 'Select modules to handle ' +
                                                 'the intercepted traffic.')

    parser.add_argument('-ti', '--targetip', dest='target_ip',
                        help='remote target IP or host name')

    parser.add_argument('-tp', '--targetport', dest='target_port', type=int,
                        help='remote target port')

    parser.add_argument('-tt', '--targetreceivetimeout', dest='target_receive_timeout', type=float,
                        default=0.25, help='Timeout in Seconds waiting for target response')
                        
    parser.add_argument('-li', '--listenip', dest='listen_ip',
                        default='0.0.0.0', help='IP address/host name to listen for ' +
                        'incoming data')

    parser.add_argument('-lp', '--listenport', dest='listen_port', type=int,
                        default=8899, help='port to listen on')

    parser.add_argument('-si', '--sourceip', dest='source_ip',
                        default='0.0.0.0', help='IP address the other end will see')

    parser.add_argument('-sp', '--sourceport', dest='source_port', type=int,
                        default=0, help='source port the other end will see')

    parser.add_argument('-om', '--outmodules', dest='out_modules',
                        help='comma-separated list of modules to modify data' +
                             ' before sending to remote target.')

    parser.add_argument('-im', '--inmodules', dest='in_modules',
                        help='comma-separated list of modules to modify data' +
                             ' received from the remote target.')

    parser.add_argument('-v', '--verbose', dest='verbose', default=True,
                        action='store_true',
                        help='More verbose output of status information')

    parser.add_argument('-n', '--no-chain', dest='no_chain_modules',
                        action='store_true', default=False,
                        help='Don\'t send output from one module to the ' +
                             'next one')

    parser.add_argument('-l', '--log', dest='logfile', default=None,
                        help='Log all data to a file before modules are run.')

    parser.add_argument('--list', dest='list', action='store_true',
                        help='list available modules')

    parser.add_argument('-lo', '--list-options', dest='help_modules', default=None,
                        help='Print help of selected module')

    return parser.parse_args()

# globals
server_communication_lock = threading.RLock()
remote_socket = None
queue = queue.SimpleQueue()
args = parse_args()

def generate_module_list(modstring, incoming=False, verbose=False):
    # This method receives the comma-separated module list, imports the modules
    # and creates a Module instance for each module. A list of these instances
    # is then returned.
    # The incoming parameter is True when the modules belong to the incoming
    # chain (-im)
    # modstring looks like mod1,mod2:key=val,mod3:key=val:key2=val2,mod4 ...
    modlist = []
    namelist = modstring.split(',')
    for n in namelist:
        name, options = parse_module_options(n)
        try:
            __import__('proxymodules.' + name)
            modlist.append(sys.modules['proxymodules.' + name].Module(incoming, verbose, options))
        except ImportError:
            print('Module %s not found' % name)
            sys.exit(3)
    return modlist


def parse_module_options(n):
    # n is of the form module_name:key1=val1:key2=val2 ...
    # this method returns the module name and a dict with the options
    n = n.split(':', 1)
    if len(n) == 1:
        # no module options present
        return n[0], None
    name = n[0]
    optionlist = n[1].split(':')
    options = {}
    for op in optionlist:
        try:
            k, v = op.split('=')
            options[k] = v
        except ValueError:
            print(op, ' is not valid!')
            sys.exit(23)
    return name, options


def list_modules():
    # show all available proxy modules
    cwd = os.getcwd()
    module_path = cwd + os.sep + 'proxymodules'
    for _, module, _ in pkgutil.iter_modules([module_path]):
        __import__('proxymodules.' + module)
        m = sys.modules['proxymodules.' + module].Module()
        print(f'{m.name} - {m.description}')


def print_module_help(modlist):
    # parse comma-separated list of module names, print module help text
    modules = generate_module_list(modlist)
    for m in modules:
        try:
            print(f'{m.name} - {m.description}')
            print(m.help())
        except AttributeError:
            print('\tNo options or missing help() function.')


def update_module_hosts(modules, source, destination):
    # set source and destination IP/port for each module
    # source and destination are ('IP', port) tuples
    # this can only be done once local and remote connections have been established
    if modules is not None:
        for m in modules:
            if hasattr(m, 'source'):
                m.source = source
            if hasattr(m, 'destination'):
                m.destination = destination


def receive_from(s):
    # receive data from a socket until no more data is there
    b = b""
    while True:
        data = s.recv(4096)
        b += data
        if not data or len(data) < 4096:
            break
    return b


def handle_data(data, modules, dont_chain, incoming, verbose):
    # execute each active module on the data. If dont_chain is set, feed the
    # output of one plugin to the following plugin. Not every plugin will
    # necessarily modify the data, though.
    for m in modules:
        vprint(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}: " + ("> > > > in: " if incoming else "< < < < out: ") + m.name, verbose)
        if dont_chain:
            m.execute(data)
        else:
            data = m.execute(data)
    return data


def open_remote_socket(args):
    remote_socket = socks.socksocket()

    try:
        if args.source_ip and args.source_port:
            remote_socket.bind((args.source_ip, args.source_port))
        remote_socket.connect((args.target_ip, args.target_port))
        vprint('Connected to %s:%d' % remote_socket.getpeername(), args.verbose)
        log(args.logfile, 'Connected to %s:%d' % remote_socket.getpeername())
    except socket.error as serr:
        if serr.errno == errno.ECONNREFUSED:
            for s in [remote_socket]:
                s.close()
            print(f'{time.strftime("%Y%m%d-%H%M%S")}, {args.target_ip}:{args.target_port}- Connection refused')
            log(args.logfile, f'{time.strftime("%Y%m%d-%H%M%S")}, {args.target_ip}:{args.target_port}- Connection refused')
            return None
        elif serr.errno == errno.ETIMEDOUT:
            for s in [remote_socket]:
                s.close()
            print(f'{time.strftime("%Y%m%d-%H%M%S")}, {args.target_ip}:{args.target_port}- Connection timed out')
            log(args.logfile, f'{time.strftime("%Y%m%d-%H%M%S")}, {args.target_ip}:{args.target_port}- Connection timed out')
            return None
        else:
            for s in [remote_socket]:
                s.close()
            raise serr
    return remote_socket

def aquire_lock(client, args, state):
  if not server_communication_lock._is_owned():
      log(args.logfile, f"{client} waiting for server lock ({state})")
      server_communication_lock.acquire()
      log(args.logfile, f"{client} aquired server lock ({state})")

def start_server_thread(args):
    global remote_socket
    # This loop ends when remote socket is not available anymore
    running = True
    try:
        while running:
            read_sockets, _, _ = select.select([remote_socket], [], [])
            for sock in read_sockets:
                try:
                    peer = sock.getpeername()
                except socket.error as serr:
                    if serr.errno == errno.ENOTCONN:
                        # kind of a blind shot at fixing issue #15
                        # I don't yet understand how this error can happen, but if it happens I'll just shut down the thread
                        # the connection is not in a useful state anymore
                        for s in [remote_socket]:
                            s.close()
                        running = False
                        break
                    else:
                        print(f"{time.strftime('%Y%m%d-%H%M%S')}: Socket exception in start_proxy_thread")
                        raise serr

                data = receive_from(sock)
                log(args.logfile, f'Received {len(data)} bytes from {peer}')

                if len(data):
                    #log(args.logfile, b'> > > in\n' + data)
                    queue.put(data)
                else:
                    vprint("Connection to remote server %s:%d closed" % peer, args.verbose)
                    log(args.logfile, "Connection to remote server %s:%d closed" % peer)
                    running = False
                    break
    except (SystemExit, KeyboardInterrupt) as e:
        raise e
    except BaseException as e:
        print('An exception occurred: {}'.format(e))
        log(args.logfile, 'An exception occurred: {}'.format(e))
    finally:
        remote_socket = None
    
def start_proxy_thread(remote_socket, local_socket, args, in_modules, out_modules):
    # This method is executed in a thread. It will relay data between the local
    # host and the remote host, while letting modules work on the data before
    # passing it on.
    
    try:
        update_module_hosts(out_modules, local_socket.getpeername(), remote_socket.getpeername())
        update_module_hosts(in_modules, remote_socket.getpeername(), local_socket.getpeername())
    except socket.error as serr:
        if serr.errno == errno.ENOTCONN:
            # kind of a blind shot at fixing issue #15
            # I don't yet understand how this error can happen, but if it happens I'll just shut down the thread
            # the connection is not in a useful state anymore
            for s in [local_socket]:
                s.close()
            return None
        else:
            for s in [local_socket]:
                s.close()
            print(f"{time.strftime('%Y%m%d-%H%M%S')}: Socket exception in start_proxy_thread")
            raise serr

    # This loop ends when no more data is received on either the local or the
    # remote socket
    server = remote_socket.getpeername()
    client = local_socket.getpeername()
    running = True
    try:
        while running:
            if remote_socket is None:
                vprint("Remote server %s:%d not available" % server, args.verbose)
                log(args.logfile, "Remote server %s:%d not available" % server)
                running = False
                break
                
            read_sockets, _, _ = select.select([local_socket], [], [])
            for sock in read_sockets:
                try:
                    peer = sock.getpeername()
                except socket.error as serr:
                    if serr.errno == errno.ENOTCONN:
                        # kind of a blind shot at fixing issue #15
                        # I don't yet understand how this error can happen, but if it happens I'll just shut down the thread
                        # the connection is not in a useful state anymore
                        for s in [local_socket]:
                            s.close()
                        running = False
                        break
                    else:
                        print(f"{time.strftime('%Y%m%d-%H%M%S')}: Socket exception in start_proxy_thread")
                        raise serr

                # Acquire the lock only if this thread doesn't already hold the lock
                aquire_lock(client, args, "receive from server")

                data = receive_from(sock)
                log(args.logfile, f'Received {len(data)} bytes from {peer}')

                if sock == local_socket:
                    if len(data):
                        log(args.logfile, b'< < < out\n' + data)
                        if out_modules is not None:
                            data = handle_data(data, out_modules,
                                               args.no_chain_modules,
                                               False,  # incoming data?
                                               args.verbose)
                        # Acquire the lock only if this thread doesn't already hold the lock
                        aquire_lock(client, args, "send to server")
                        remote_socket.send(data.encode() if isinstance(data, str) else data)
                        # get server data
                        try:
                            data = queue.get(True, args.target_receive_timeout)
                        except:
                            data = ""
                        if len(data):
                            log(args.logfile, b'> > > in\n' + data)
                            if in_modules is not None:
                                data = handle_data(data, in_modules,
                                                   args.no_chain_modules,
                                                   True,  # incoming data?
                                                   args.verbose)
                            local_socket.send(data)
                        else:
                            #vprint("No data received from remote server %s:%d" % server, args.verbose)
                            log(args.logfile, "No data received from remote server %s:%d" % server)
                            #local_socket.close()
                            #running = False
                            break
                            
                        # Release the lock only if this thread holds the lock
                        if server_communication_lock._is_owned():
                            #time.sleep(0.060)
                            server_communication_lock.release()
                            log(args.logfile, "%s:%d released server lock" % client)
                        else:
                            log(args.logfile, "%s:%d has no server lock" % client)
                    else:
                        vprint("Connection from local client %s:%d closed" % peer, args.verbose)
                        log(args.logfile, "Connection from local client %s:%d closed" % peer)
                        running = False
                        break

    finally:
        # Release the lock only if this thread holds the lock
        if server_communication_lock._is_owned():
            server_communication_lock.release()
            
def log(handle, message, message_only=False):
    # if message_only is True, only the message will be logged
    # otherwise the message will be prefixed with a timestamp and a line is
    # written after the message to make the log file easier to read
    if not isinstance(message, bytes):
        message = bytes(message, 'ascii')
    if handle is None:
        return
    if not message_only:
        logentry = bytes("%s %s\n" % (time.strftime('%Y%m%d-%H%M%S'), str(time.time())), 'ascii')
    else:
        logentry = b''
    logentry += message
    if not message_only:
        logentry += b'\n' + b'-' * 20 + b'\n'
    handle.write(logentry)


def vprint(msg, is_verbose):
    # this will print msg, but only if is_verbose is True
    if is_verbose:
        print(msg)

def signal_handler(signal, frame):
    global args
    log(args.logfile, 'Ctrl+C detected, exiting...')
    print('\nCtrl+C detected, exiting...')
    sys.exit(0)

def main():
    global args, remote_socket

    signal.signal(signal.SIGINT, signal_handler)
    if args.list is False and args.help_modules is None:
        if not args.target_ip:
            print('Target IP is required: -ti')
            sys.exit(6)
        if not args.target_port:
            print('Target port is required: -tp')
            sys.exit(7)

    if args.logfile is not None:
        try:
            args.logfile = open(args.logfile, 'ab', 0)  # unbuffered
        except Exception as ex:
            print('Error opening logfile')
            print(ex)
            sys.exit(4)

    if args.list:
        list_modules()
        sys.exit(0)

    if args.help_modules is not None:
        print_module_help(args.help_modules)
        sys.exit(0)

    if args.listen_ip != '0.0.0.0' and not is_valid_ip4(args.listen_ip):
        try:
            ip = socket.gethostbyname(args.listen_ip)
        except socket.gaierror:
            ip = False
        if ip is False:
            print('%s is not a valid IP address or host name' % args.listen_ip)
            sys.exit(1)
        else:
            args.listen_ip = ip

    if not is_valid_ip4(args.target_ip):
        try:
            ip = socket.gethostbyname(args.target_ip)
        except socket.gaierror:
            ip = False
        if ip is False:
            print('%s is not a valid IP address or host name' % args.target_ip)
            sys.exit(2)
        else:
            args.target_ip = ip

    if args.in_modules is not None:
        in_modules = generate_module_list(args.in_modules, incoming=True, verbose=args.verbose)
    else:
        in_modules = None

    if args.out_modules is not None:
        out_modules = generate_module_list(args.out_modules, incoming=False, verbose=args.verbose)
    else:
        out_modules = None

    # this is the socket we will listen on for incoming connections
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        proxy_socket.bind((args.listen_ip, args.listen_port))
    except socket.error as e:
        print(e.strerror)
        sys.exit(5)

    proxy_socket.listen(100)
    log(args.logfile, str(args))
    # endless loop until ctrl+c
    running = True
    while running:
        try:
            if remote_socket is None:
                remote_socket = open_remote_socket(args)
                server_thread = threading.Thread(target=start_server_thread,
                                                args=[args])
                log(args.logfile, "Starting server thread " + server_thread.name)
                server_thread.start()
         
            in_socket, in_addrinfo = proxy_socket.accept()
            vprint('Connection from %s:%d' % in_addrinfo, args.verbose)
            log(args.logfile, 'Connection from %s:%d' % in_addrinfo)
            proxy_thread = threading.Thread(target=start_proxy_thread,
                                            args=(remote_socket, in_socket, args, in_modules,
                                                  out_modules))
            log(args.logfile, "Starting proxy thread " + proxy_thread.name)
            proxy_thread.start()
        except (SystemExit, KeyboardInterrupt):
            running = False
        except BaseException as e:
            print('An exception occurred: {}'.format(e))
            log(args.logfile, 'An exception occurred: {}'.format(e))

if __name__ == '__main__':
    main()