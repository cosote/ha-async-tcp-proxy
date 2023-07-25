#!/usr/bin/with-contenv bashio

# Create main config
CONFIG_LISTENPORT=$(bashio::config 'listenport')
CONFIG_HOST=$(bashio::config 'targethost')
CONFIG_PORT=$(bashio::config 'targetport')
CONFIG_TIMEOUT=$(bashio::config 'receive_timeout')
CONFIG_LOGLEVEL=$(bashio::config 'loglevel')

echo "Preparing to run async-tcp-proxy"
echo "Listen on port: $CONFIG_LISTENPORT"
echo "Target Server: $CONFIG_HOST:$CONFIG_PORT"
echo "Timeout: $CONFIG_TIMEOUT"
echo "Loglevel: $CONFIG_LOGLEVEL"
ls / -name "async-tcp-proxy.py"
python async-tcp-proxy.py -ti ${CONFIG_HOST} -tp ${CONFIG_PORT} -tt ${CONFIG_TIMEOUT} -lp ${CONFIG_LISTENPORT}