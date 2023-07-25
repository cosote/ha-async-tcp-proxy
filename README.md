# Home Assistant AddOn Async TCP Proxy

It's a simple TCP Proxy addon.
I created it, because none of the existing modbus proxies worked for me on PE11 devices in any of the device modes.
I needed a reliable communication between my Deye SUN-10K-SG04LP3-EU hybrid-inverter and SDM630v2.
At the same time I use HA modbus, to read certain registers from the energy meter, and without a proxy, it's problematic.

One PE11 is connected to SDM630v2 and is the single RS485 master for the SDM630 client. Is running as a tcp-server
(in serial protocol none config) and configureed in the proxy addon as the target (server) host. HS modbus is polling
registers in rtuovertcp mode. The second PE11 is connected to the modus energy port on the Deye inverter and configured
as tcp-client (also with serial protocol none config).

The addon has only been tested on HA modbus integration with SDM630v2 and PE11 devices, see http://www.hi-flying.com/pe11.

## Installation
[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fcosote%2Fha-async-tcp-proxy)
- Add This [Repository](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fcosote%2Fha-async-tcp-proxy) (Or click Button above)
- Install Asny TCP Proxy from the Add-On Store

## Configuration
- To be added

### Configuration Tab
<img width="400" src="https://somthing.png">

### Output after Start
<img width="1000" src="https://somthing.png">

## Mentions
This addon based on tcpproxy by René Werner, https://github.com/ickerwx/tcpproxy
