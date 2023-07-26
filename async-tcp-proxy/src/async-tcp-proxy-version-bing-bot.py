import argparse
import asyncio
import logging

MAX_CLIENT_TIMEOUT = 60
BUFFER_SIZE = 2 ** 12 # 4kb
CLOSE_REMOTE_SERVER_NO_DATA_RECEIVED_COUNT = 5
remote_server_no_data_received_count = 0

# Create a lock to synchronize access to the remote server
remote_server_lock = asyncio.Lock()

# Create a global variable to store the remote server connection
remote_server_connection = None
async def get_remote_server_connection():
    global remote_server_connection
    global remote_server_no_data_received_count
    if not remote_server_connection:
        try:
            remote_reader, remote_writer = await asyncio.open_connection(args.server_host, args.server_port)
            remote_server_connection = (remote_reader, remote_writer)
            remote_server_no_data_received_count = 0
        except (ConnectionError, asyncio.TimeoutError) as e:
            logging.error(f'Error connecting to remote server: {e}')
            return
    return remote_server_connection

def close_remote_server_connection(reason):
    global remote_server_connection
    logging.warning(f'Closing remote server connection, reason: {reason}')
    reader, writer = remote_server_connection
    remote_server_connection = None
    writer.close()
    return reader, writer
   
async def handle_client(reader, writer):
    try:
        global remote_server_no_data_received_count
        
        client_address = writer.get_extra_info('peername')
        log = logging.getLogger(client_address[0])
        log.info(f'New client connection')

        # Check if a connection to the remote server already exists
        async with remote_server_lock:
            remote_reader, remote_writer = await get_remote_server_connection()

        # main client loop waiting to handle proxy communication
        while True:
            client_in_session = False
            try:
                data = await asyncio.wait_for(reader.read(BUFFER_SIZE), timeout=MAX_CLIENT_TIMEOUT)
                if data:
                    log.debug(f'Received {len(data)} bytes from client (new session)')
                else:
                    continue
            except asyncio.TimeoutError:
                continue
            except ConnectionError as e:
                log.error(f'Error reading from client: {e}')
                break
            
            # Acquire the lock before waiting for additional data from the client
            async with remote_server_lock:
                # start client "session" with defined client_timeout
                while True:
                    if client_in_session:
                        try:
                            data = await asyncio.wait_for(reader.read(BUFFER_SIZE), timeout=args.client_timeout)
                            if data:
                                log.debug(f'Received {len(data)} bytes from client (existing session)')
                            else:
                                break
                        except asyncio.TimeoutError:
                            break
                        except ConnectionError as e:
                            log.error(f'Error reading from client: {e}')
                            break
                    
                    # now client sesssion starts and short client read timeout is used
                    client_in_session = True
                    try:
                        # Forward data to remote server
                        remote_writer.write(data)
                        log.debug(f'Sent {len(data)} bytes to remote server')
                    except ConnectionError as e:
                        log.error(f'Error writing to remote server: {e}')
                        close_remote_server_connection(e)
                        return
                    
                    try:
                        # Read response from remote server
                        response = await asyncio.wait_for(remote_reader.read(BUFFER_SIZE), timeout=args.server_timeout)
                        if not response:
                            break
                        remote_server_no_data_received_count = 0
                        log.debug(f'Received {len(response)} bytes from remote server')
                    except asyncio.TimeoutError:
                        remote_server_no_data_received_count += 1
                        if remote_server_no_data_received_count >= CLOSE_REMOTE_SERVER_NO_DATA_RECEIVED_COUNT:
                            close_remote_server_connection(f'For {remote_server_no_data_received_count} times not data received')
                            return
                        break
                    except ConnectionError as e:
                        log.error(f'Error reading from remote server: {e}')
                        close_remote_server_connection(e)
                        return
                        
                    try:
                        # Send response to client
                        writer.write(response)
                        log.debug(f'Sent {len(response)} bytes to client')
                    except ConnectionError as e:
                        log.error(f'Error writing to client: {e}')
                        break
    finally:
        writer.close()
        
async def main():
    parser = argparse.ArgumentParser(description='TCP proxy server')
    parser.add_argument('--port', type=int, default=8899, help='proxy server port')
    parser.add_argument('--server-host', type=str, default='192.168.177.202', help='server host')
    parser.add_argument('--server-port', type=int, default=8899, help='server port')
    parser.add_argument('--server-timeout', type=float, default=0.15, help='timeout for server response')
    parser.add_argument('--client-timeout', type=float, default=0.15, help='timeout for additional client requests')
    parser.add_argument('--loglevel', type=str, default='INFO', help='log level: DEBUG, INFO, WARNING, ERROR, CRITICAL')
    
    global args
    args = parser.parse_args()

    # init logging
    logging.basicConfig(level=args.loglevel.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # start proxy server
    server = await asyncio.start_server(handle_client, '0.0.0.0', args.port)
    async with server:
        logging.info(f'TCP proxy server started on port {args.port}')
        await server.serve_forever()

asyncio.run(main())
