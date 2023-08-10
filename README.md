# Home Assistant AddOn Async TCP Proxy

It's a simple TCP Proxy addon.
I created it, because none of the existing modbus proxies worked for me on PE11 devices in any of the device modes.
I needed a reliable communication between my Deye SUN-10K-SG04LP3-EU hybrid-inverter and SDM630v2.
At the same time I use HA modbus, to read certain registers from the energy meter, and without a proxy, it's problematic.

One PE11 is connected to SDM630v2 and is the single RS485 master for the SDM630 client. It's running as a tcp-server
(in serial protocol none config) and configured in the proxy addon as the target (server) host. HA modbus is polling
registers in rtuovertcp mode. The second PE11 is connected to the modbus energy meter port on the Deye inverter and configured
as tcp-client (also with serial protocol none config) to my HA host on this proxy port.

The addon has been only tested on HA modbus integration with SDM630v2 and PE11 devices on Deye inverter, see [PE11](http://www.hi-flying.com/pe11).

## Installation
[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fcosote%2Fha-async-tcp-proxy)
- Add This [Repository](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fcosote%2Fha-async-tcp-proxy) (Or click Button above)
- Install Async TCP Proxy from the Add-On Store

## Configuration
- The **server_host** and **server_port** are the first settings you need to update. This is the TCP-server behind the proxy and all client requests will be forwarded to that server.
- Once a client sends data to the proxy, the following communication is synchronized and blocking any other client from getting processed. As the server behind the proxy might not reply with data instantly or not at all, **server_timeout** waits specified Seconds for that response, that will be then passed back to the client or breaks to allow other clients to be processed. The server_timeout number must be greater than 0 or no data would be received from the server.
- The **client_timeout** allows a bulk of packages from the same client to be processed in its current lock, without getting interrupted by other clients. If the client_timeout is 0, this functionality is disabled.
- In **loglevel** Info, we see only logs about new and closed client connections. When using **DEBUG**, every packet communication or experienced timeout will be logged.

### Configuration Tab
![image](https://github.com/cosote/ha-async-tcp-proxy/assets/15175818/e08214b3-c4a1-4817-b4c4-21c351ac7f77)

### Log Tab
![image](https://github.com/cosote/ha-async-tcp-proxy/assets/15175818/c325fd04-bff4-4b06-b136-ef436b5e854d)

## TODO
- Add support for multiple servers behind the proxy on different ports
- Auto detect/custom client request detection when server will not respond
- Modbus protocol parsing and custom data manipulation
- General code improvements/refactoring

## Other proxies
Though all these proxies had issues with my Deye inverter or the PE11 protocol settings (none or Modbus), these proxies really look good.
One addition of those is, that they decode the Modus packets (except for tcpproxy), what ha-async-tcp-proxy is currently not doing (on purpose, probably in future?).
- https://pypi.org/project/modbus-proxy
- https://github.com/Akulatraxas/ha-modbusproxy
- https://docs.evcc.io/docs/reference/configuration/modbusproxy
- https://github.com/ickerwx/tcpproxy
