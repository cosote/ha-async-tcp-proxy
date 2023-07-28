#!/usr/bin/with-contenv bashio

# Create main config
CONFIG_SERVER_HOST=$(bashio::config 'server_host')
CONFIG_SERVER_PORT=$(bashio::config 'server_port')
CONFIG_SERVER_TIMEOUT=$(bashio::config 'server_timeout')
CONFIG_CLIENT_TIMEOUT=$(bashio::config 'client_timeout')
CONFIG_LOGLEVEL=$(bashio::config 'loglevel')

echo "Preparing to run async-tcp-proxy"
echo "Server: $CONFIG_SERVER_HOST:$CONFIG_SERVER_PORT"
echo "Server timeout: $CONFIG_SERVER_TIMEOUT"
echo "Client timeout: $CONFIG_CLIENT_TIMEOUT"
echo "Loglevel: $CONFIG_LOGLEVEL"

execute="python async-tcp-proxy.py --port 8899 --server-host $CONFIG_SERVER_HOST --server-port $CONFIG_SERVER_PORT --server-timeout $CONFIG_SERVER_TIMEOUT --client-timeout $CONFIG_CLIENT_TIMEOUT --loglevel $CONFIG_LOGLEVEL"

echo Execute: $execute
$execute
