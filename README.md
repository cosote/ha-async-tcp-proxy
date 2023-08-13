# Home Assistant AddOn Async TCP Proxy

It's a simple TCP Proxy addon. I created it, because none of the existing modbus proxies worked for me on PE11 devices in any of the device modes. I needed a reliable communication between my Deye SUN-10K-SG04LP3-EU hybrid-inverter and SDM630v2. At the same time I use HA modbus to read certain registers from the energy meter, and without a proxy, it's really problematic, as there's no free time-window due to the Deye inverter sending 3 requests or so per Second.

One PE11 is connected to SDM630v2 and is the single RS485 master for the SDM630 client. It's running as a tcp-server (in serial protocol none config) and configured in the proxy addon as the server behind the proxy. HA modbus is polling registers in rtuovertcp mode connected to the addon exposed port running on HA. The second PE11 is connected to the modbus energy meter port on the Deye inverter and configured as tcp-client (also with serial protocol none config) also to my HA host on this proxy port.

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
- Collect statistics to simplify timeout adjustments
- General code improvements/refactoring
- Add support for multiple servers behind the proxy on different exposed ports (fixed number of 3?)
- Support client request where server will never respond (Deye sends some tcp packages that don't create a response on PE11 server)
- Modbus protocol parsing and custom data manipulation (e.g. change Modbus identifier or so)

## Other proxies
Though all these proxies had issues with my Deye inverter or the PE11 protocol settings (none or Modbus), these proxies really look good.
One addition of those is, that they decode the Modbus packets (except for tcpproxy), what ha-async-tcp-proxy is currently not doing (on purpose, probably in future?).
- https://pypi.org/project/modbus-proxy
- https://github.com/Akulatraxas/ha-modbusproxy
- https://docs.evcc.io/docs/reference/configuration/modbusproxy
- https://github.com/ickerwx/tcpproxy

## My configuration
The default async-tcp-proxy addon configuration is based on my HA setup. The PE11 TCP-Server is running on IP 192.168.177.202:8899 and connected with 38400 baud, 8 data bit, 1 stop bit and none parity to my SDM630v2. This PE11 TCP-Server is configured behind the proxy.

### Two clients are configured to connect to the proxy
The async-tcp-proxy is running on my HA system on IP 192.168.177.222:8899 with these clients accessing it:
- PE11 TCP-Client connected to the Deye Inverter on the RS485 modbus port for energy meter
- HA modbus integration, see my yaml configuration here:
  <details><summary>Sample HA modbus yaml</summary>

  ```yaml
  # Used in dashboards:
  # sdm630_total_energy
  # sdm630_total_power_consumption
  # sdm630_frequency_of_supply_voltages
  # sdm630_phase_1_export_active_energy
  # sdm630_phase_2_export_active_energy
  # sdm630_phase_3_export_active_energy
  # sdm630_phase_1_import_active_energy
  # sdm630_phase_2_import_active_energy
  # sdm630_phase_3_import_active_energy
  modbus:
  - name: sdm630
    host: localhost
    port: 8899
    #type: tcp udp serial rtuovertcp
    type: rtuovertcp
    close_comm_on_error: false
    retries: 0
    timeout: 1
    #retry_on_empty: true
    sensors:
      # SDM630 modbus registers 27 - 36
      - name: sdm_630_registers_27_36
        unique_id: sdm_630_registers_27_36
        address: 52
        input_type: input
        count: 20
        data_type: custom
        structure: ">10f"
        precision: 5
        scan_interval: 5
  
      # SDM630 modbus registers 172 - 179
      - name: sdm_630_registers_172_179
        unique_id: sdm_630_registers_172_179
        address: 342
        input_type: input
        count: 16
        data_type: custom
        structure: ">8f"
        precision: 3
        scan_interval: 5

  template:
    - sensor:
      # Total system power.
      - unique_id: sdm630_total_power_consumption
        name: sdm630_total_power_consumption
        state: >
          {% set last_value = states('sensor.sdm630_total_power_consumption') | float(0) %}
          {% set curr_value = states('sensor.sdm_630_registers_27_36').split(',')[0] | float(0) %}
          {% if curr_value == 0 %}{{ last_value }}{% else %}{{ curr_value }}{% endif %}
        attributes:
          friendly_name: 'Total system power.'
        unit_of_measurement: W
        device_class: power
      # Frequency of supply voltages
      - unique_id: sdm630_frequency_of_supply_voltages
        name: sdm630_frequency_of_supply_voltages
        state: >
          {% set last_value = states('sensor.sdm630_frequency_of_supply_voltages') | float(0) %}
          {% set curr_value = states('sensor.sdm_630_registers_27_36').split(',')[9] | float(0) %}
          {% if curr_value == 0 %}{{ last_value }}{% else %}{{ curr_value }}{% endif %}
        attributes:
          friendly_name: 'Frequency of supply voltages'
        unit_of_measurement: Hz
        device_class: frequency
      # Total active energy
      - unique_id: sdm630_total_energy
        name: sdm630_total_energy
        state: >
          {% set last_value = states('sensor.sdm630_total_energy') | float(0) %}
          {% set curr_value = states('sensor.sdm_630_registers_172_179').split(',')[0] | float(0) %}
          {% if curr_value == 0 %}{{ last_value }}{% else %}{{ curr_value }}{% endif %}
        attributes:
          friendly_name: 'Total active energy'
        unit_of_measurement: kWh
        device_class: energy
        state_class: total
      # Phase 1 import active energy
      - unique_id: sdm630_phase_1_import_active_energy
        name: sdm630_phase_1_import_active_energy
        state: >
          {% set last_value = states('sensor.sdm630_phase_1_import_active_energy') | float(0) %}
          {% set curr_value = states('sensor.sdm_630_registers_172_179').split(',')[2] | float(0) %}
          {% if curr_value == 0 %}{{ last_value }}{% else %}{{ curr_value }}{% endif %}
        attributes:
          friendly_name: 'Phase 1 import active energy'
        unit_of_measurement: kWh
        device_class: energy
        state_class: total
      # Phase 2 import active energy
      - unique_id: sdm630_phase_2_import_active_energy
        name: sdm630_phase_2_import_active_energy
        state: >
          {% set last_value = states('sensor.sdm630_phase_2_import_active_energy') | float(0) %}
          {% set curr_value = states('sensor.sdm_630_registers_172_179').split(',')[3] | float(0) %}
          {% if curr_value == 0 %}{{ last_value }}{% else %}{{ curr_value }}{% endif %}
        attributes:
          friendly_name: 'Phase 2 import active energy'
        unit_of_measurement: kWh
        device_class: energy
        state_class: total
      # Phase 3 import active energy
      - unique_id: sdm630_phase_3_import_active_energy
        name: sdm630_phase_3_import_active_energy
        state: >
          {% set last_value = states('sensor.sdm630_phase_3_import_active_energy') | float(0) %}
          {% set curr_value = states('sensor.sdm_630_registers_172_179').split(',')[4] | float(0) %}
          {% if curr_value == 0 %}{{ last_value }}{% else %}{{ curr_value }}{% endif %}
        attributes:
          friendly_name: 'Phase 3 import active energy'
        unit_of_measurement: kWh
        device_class: energy
        state_class: total
      # Phase 1 export active energy
      - unique_id: sdm630_phase_1_export_active_energy
        name: sdm630_phase_1_export_active_energy
        state: >
          {% set last_value = states('sensor.sdm630_phase_1_export_active_energy') | float(0) %}
          {% set curr_value = states('sensor.sdm_630_registers_172_179').split(',')[5] | float(0) %}
          {% if curr_value == 0 %}{{ last_value }}{% else %}{{ curr_value }}{% endif %}
        attributes:
          friendly_name: 'Phase 1 export active energy'
        unit_of_measurement: kWh
        device_class: energy
        state_class: total
      # Phase 2 export active energy
      - unique_id: sdm630_phase_2_export_active_energy
        name: sdm630_phase_2_export_active_energy
        state: >
          {% set last_value = states('sensor.sdm630_phase_2_export_active_energy') | float(0) %}
          {% set curr_value = states('sensor.sdm_630_registers_172_179').split(',')[6] | float(0) %}
          {% if curr_value == 0 %}{{ last_value }}{% else %}{{ curr_value }}{% endif %}
        attributes:
          friendly_name: 'Phase 2 export active energy'
        unit_of_measurement: kWh
        device_class: energy
        state_class: total
      # Phase 3 export active energy
      - unique_id: sdm630_phase_3_export_active_energy
        name: sdm630_phase_3_export_active_energy
        state: >
          {% set last_value = states('sensor.sdm630_phase_3_export_active_energy') | float(0) %}
          {% set curr_value = states('sensor.sdm_630_registers_172_179').split(',')[7] | float(0) %}
          {% if curr_value == 0 %}{{ last_value }}{% else %}{{ curr_value }}{% endif %}
        attributes:
          friendly_name: 'Phase 3 export active energy'
        unit_of_measurement: kWh
        device_class: energy
        state_class: total

  utility_meter:
    # Total active energy Today
    sdm630_total_energy_today:
      name: sdm630_total_energy_today
      unique_id: sdm630_total_energy_today
      source: sensor.sdm630_total_energy
      cycle: daily
  ```
  </details>
  
### PE11 TCP-Server on SDM630v2
<details><summary>Serial Port Settings</summary>

![image](https://github.com/cosote/ha-async-tcp-proxy/assets/15175818/3e5cdb1c-54b2-4d18-b2db-e333286f272f)
</details>

<details><summary>Communication Settings</summary>

![image](https://github.com/cosote/ha-async-tcp-proxy/assets/15175818/a5470e26-da0e-4321-98bc-2b6013632bbe)
</details>

### PE11 TCP-Client on Deye inverter
<details><summary>Serial Port Settings</summary>

![image](https://github.com/cosote/ha-async-tcp-proxy/assets/15175818/c05aaf5c-7e95-454f-a45d-3aa20b280f53)
</details>

<details><summary>Communication Settings</summary>

![image](https://github.com/cosote/ha-async-tcp-proxy/assets/15175818/ab36dbd6-f4f3-4ce7-ac0e-41172653a2de)
</details>
