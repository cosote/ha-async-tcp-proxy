#!/usr/bin/with-contenv bashio

# Create main config
CONFIG_PORT=$(bashio::config 'port')
CONFIG_SERVER_HOST=$(bashio::config 'server_host')
CONFIG_SERVER_PORT=$(bashio::config 'server_port')
CONFIG_SERVER_TIMEOUT=$(bashio::config 'server_timeout')
CONFIG_CLIENT_TIMEOUT=$(bashio::config 'client_timeout')
CONFIG_LOGLEVEL=$(bashio::config 'loglevel')
CONFIG_PROXY_IMPLEMENTATION=$(bashio::config 'implementation')

echo "Preparing to run async-tcp-proxy"
echo "Using implementation: $CONFIG_PROXY_IMPLEMENTATION"
echo "Listen on port: $CONFIG_PORT"
echo "Server: $CONFIG_SERVER_HOST:$CONFIG_SERVER_PORT"
echo "Server timeout: $CONFIG_SERVER_TIMEOUT"
echo "Client timeout: $CONFIG_CLIENT_TIMEOUT"
echo "Loglevel: $CONFIG_LOGLEVEL"

if [ "$CONFIG_PROXY_IMPLEMENTATION" = "default" ]; then
  execute="python async-tcp-proxy.py --port $CONFIG_PORT --server-host $CONFIG_SERVER_HOST --server-port $CONFIG_SERVER_PORT --server-timeout $CONFIG_SERVER_TIMEOUT --client-timeout $CONFIG_CLIENT_TIMEOUT --loglevel $CONFIG_LOGLEVEL"
else
  execute="python async-tcp-proxy-alternative.py -lp $CONFIG_PORT -ti $CONFIG_SERVER_HOST -tp $CONFIG_SERVER_PORT -tt $CONFIG_SERVER_TIMEOUT"
fi

echo Execute: $execute
$execute
