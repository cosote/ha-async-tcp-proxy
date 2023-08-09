#
# This file is part of the ha-async-tcp-proxy project
#
# Copyright (c) 2023 Jens Bornemann
#
# Distributed under the Apache 2.0. See LICENSE for more info.
#

import argparse
import asyncio
import logging

# Default timeout waiting for client to request data from remote server
MAX_CLIENT_TIMEOUT = 60

# Default communication buffer size of 4kb
BUFFER_SIZE = 2 ** 12

# Create a lock to synchronize access to the remote server
remote_server_lock = asyncio.Lock()

# Create a global variable to store the remote server connection
remote_server_connection = None

async def get_remote_server_connection(log):
    global remote_server_connection
    if not remote_server_connection:
        try:
            remote_reader, remote_writer = await asyncio.open_connection(args.server_host, args.server_port)
            remote_server_connection = (remote_reader, remote_writer)
        except (ConnectionError, asyncio.TimeoutError) as e:
            log.error(f'Error connecting to remote server: {e}')
            return
    return remote_server_connection

def close_remote_server_connection(log, reason):
    global remote_server_connection
    log.warning(f'Closing remote server connection, reason: {reason}')
    reader, writer = remote_server_connection
    remote_server_connection = None
    writer.close()
    return reader, writer

# Source: https://code.activestate.com/recipes/142812-hex-dumper/
hex_dump_FILTER=''.join([(len(repr(chr(x)))==3) and chr(x) or '.' for x in range(256)])
def hex_dump(src, length=8):
    N=0; result=''
    while src:
       s,src = src[:length],src[length:]
       hexa = ' '.join(["%02X"%ord(x) for x in s])
       s = s.translate(hex_dump_FILTER)
       result += "%04X   %-*s   %s\n" % (N, length*3, hexa, s)
       N+=length
    return result

async def handle_client(reader, writer):
    try:
        MAX_TIMEOUTS = 5
        timeout_count = 0
        return_reason = 'unknown'

        client_address = writer.get_extra_info('peername')

        # get logging for this client connection with ip address and port
        log = logging.getLogger(f'{client_address[0]}:{client_address[1]}')
        log.info(f'New client connection')

        # Check if a connection to the remote server already exists
        async with remote_server_lock:
            remote_reader, remote_writer = await get_remote_server_connection(log)

        # main client loop waiting to handle proxy communication for client
        while True:
            # Wait MAX_CLIENT_TIMEOUT for client to request data from remote server
            client_in_session = False
            try:
                data = await asyncio.wait_for(reader.read(BUFFER_SIZE), timeout=MAX_CLIENT_TIMEOUT)
                if data:
                    log.debug(f'Received {len(data)} bytes from client (new session)')
                else:
                    return_reason = f'No data received from client (new session)'
                    log.debug(return_reason)
                    return
            except asyncio.TimeoutError:
                log.debug(f'Timeout receiving from client (new session)')
                continue
            except ConnectionError as e:
                return_reason = f'Error reading from client: {e}'
                log.error(return_reason)
                return

            # Acquire the lock to ensure this client communicates to remote server exclusively
            async with remote_server_lock:
                # Start client "session" with defined client_timeout
                while True:
                    if client_in_session:
                        try:
                            data = await asyncio.wait_for(reader.read(BUFFER_SIZE), timeout=args.client_timeout)
                            if data:
                                log.debug(f'Received {len(data)} bytes from client (existing session)')
                            else:
                                log.debug(f'No data received from client (existing session)')
                                break
                        except asyncio.TimeoutError:
                            log.debug(f'Timeout receiving from client (existing session)')
                            break
                        except ConnectionError as e:
                            return_reason = f'Connection error reading from client: {e}'
                            return
                        except Excpetion as e:
                            return_reason = f'Error reading from client: {e}'
                            return

                    # Client sesssion starts now and short client read timeout is used
                    client_in_session = True
                    try:
                        # Forward data to remote server
                        _, remote_writer = await get_remote_server_connection(log)
                        remote_writer.write(data)
                        log.debug(f'Sent {len(data)} bytes to remote server')
                    except ConnectionError as e:
                        return_reason = f'Connection error writing to remote server: {e}'
                        log.error(return_reason)
                        close_remote_server_connection(log, e)
                        return
                    except Excpetion as e:
                        return_reason = f'Error writing to remote server: {e}'
                        log.error(return_reason)
                        close_remote_server_connection(log, e)
                        return

                    try:
                        # Read response from remote server
                        remote_reader, _ = await get_remote_server_connection(log)
                        response = await asyncio.wait_for(remote_reader.read(BUFFER_SIZE), timeout=args.server_timeout)
                        if not response:
                            break
                        timeout_count = 0
                        log.debug(f'Received {len(response)} bytes from remote server')
                    except asyncio.TimeoutError:
                        # Remote server didn't respond in time
                        log.debug(f'No response from remote server for client request:\n{hex_dump(data)}')
                        timeout_count += 1
                        if timeout_count >= MAX_TIMEOUTS:
                            # We've reached the maximum number of timeouts from server and close remote server connection
                            return_reason = f'For {timeout_count} times no data received from remote server'
                            close_remote_server_connection(log, return_reason)
                            return
                        break
                    except ConnectionError as e:
                        return_reason = f'Connection error reading from remote server: {e}'
                        log.error(return_reason)
                        close_remote_server_connection(log, e)
                        return
                    except Excpetion as e:
                        return_reason = f'Error reading from remote server: {e}'
                        log.error(return_reason)
                        close_remote_server_connection(log, e)
                        return

                    try:
                        # Send response to client
                        writer.write(response)
                        log.debug(f'Sent {len(response)} bytes to client')
                    except ConnectionError as e:
                        return_reason = f'Connection error writing to client: {e}'
                        return
                    except Excpetion as e:
                        return_reason = f'Error writing to client: {e}'
                        return
    finally:
        log.info(f'Closing client connection, reason: {return_reason}')
        writer.close()

async def main():
    parser = argparse.ArgumentParser(description='TCP proxy server')
    parser.add_argument('--port', type=int, default=8899, help='proxy server port')
    parser.add_argument('--server-host', type=str, default='192.168.177.202', help='server host')
    parser.add_argument('--server-port', type=int, default=8899, help='server port')
    parser.add_argument('--server-timeout', type=float, default=0.15, help='timeout for server response')
    parser.add_argument('--client-timeout', type=float, default=0.15, help='timeout for additional client requests')
    parser.add_argument('--loglevel', type=str, default='INFO', help='log level: NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL')

    global args
    args = parser.parse_args()

    # Initialize logging
    logging.basicConfig(level=args.loglevel.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Start proxy server
    try:
        server = await asyncio.start_server(handle_client, '0.0.0.0', args.port)
        async with server:
            logging.info(f'TCP proxy server started on port {args.port}')
            await server.serve_forever()
    except Excpetion as e:
        logging.critical(f'Critical error: {e}')

asyncio.run(main())
