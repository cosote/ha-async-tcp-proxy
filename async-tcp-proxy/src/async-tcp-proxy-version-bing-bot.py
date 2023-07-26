import argparse
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

# Create a lock to synchronize access to the remote server
remote_server_lock = asyncio.Lock()

# Create a global variable to store the remote server connection
remote_server_connection = None

async def handle_client(reader, writer):
    global remote_server_connection

    client_address = writer.get_extra_info('peername')
    logging.info(f'New client connection from {client_address}')

    # Check if a connection to the remote server already exists
    async with remote_server_lock:
        if not remote_server_connection:
            try:
                remote_reader, remote_writer = await asyncio.wait_for(asyncio.open_connection(args.server_host, args.server_port), timeout=args.server_timeout)
                remote_server_connection = (remote_reader, remote_writer)
            except (ConnectionError, asyncio.TimeoutError) as e:
                logging.error(f'Error connecting to remote server: {e}')
                writer.close()
                return
        else:
            remote_reader, remote_writer = remote_server_connection

    while True:
        try:
            # Acquire the lock before waiting for additional data from the client
            async with remote_server_lock:
                data = await asyncio.wait_for(reader.read(1024), timeout=args.client_timeout)
                if not data:
                    break

                logging.info(f'Received {len(data)} bytes from {client_address}')

                # Communicate with the remote server
                remote_writer.write(data)
                response = await remote_reader.read(1024)

                # Send response to client
                writer.write(response)
                logging.info(f'Sent {len(response)} bytes to {client_address}')
        except (ConnectionError, asyncio.TimeoutError) as e:
            logging.error(f'Error reading from client, communicating with remote server or writing to client: {e}')
            break

    writer.close()

async def main():
    parser = argparse.ArgumentParser(description='TCP proxy server')
    parser.add_argument('--port', type=int, default=8899, help='proxy server port')
    parser.add_argument('--server-host', type=str, default='192.168.177.202', help='server host')
    parser.add_argument('--server-port', type=int, default=8899, help='server port')
    parser.add_argument('--server-timeout', type=float, default=0.25, help='timeout for server response')
    parser.add_argument('--client-timeout', type=float, default=0.1, help='timeout for additional client requests')
    global args
    args = parser.parse_args()

    server = await asyncio.start_server(handle_client, '0.0.0.0', args.port)
    async with server:
        logging.info(f'TCP proxy server started on port {args.port}')
        await server.serve_forever()

asyncio.run(main())
