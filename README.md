# ha_ev_smartcharge
A crude take on smart charging using Home Assistant. Made for two Easee Home chargers and two BMWs. Tested for BMWs using the [BMW Connected Drive](https://www.home-assistant.io/integrations/bmw_connected_drive/) integration and [Easee Home](https://github.com/fondberg/easee_hass) chargers, but the principles used should be valid for any car make and charger (provided the car and charger have accessible APIs).

# The parts
The solution consists of three main parts: <br>
* An AppDaemon app called `strompris` whose main output in the EV smartcharge context is an attribute called `sorted_strompris` which gives today's (and tomorrow's, if available) hourly energy prices in sorted order (cheap to expensive)
* An AppDaemon app called `elbillading` that, based on the current State of Charge (SOC) of the car's battery, the desired end SOC (after charging), and the desired departure time, selects during which hours (between now and the desired departure time) the car should be able to charge
* Home Assistant packages for each car and each charger. <br>
  * For each car, the packages contain:<br>
    * Helpers for setting parameters for the car <br>
      * Charging goal
      * Minimum charge
      * Battery capacity
      * Maximum charging power
      * Charging losses (since not all the power delivered from the charger ends up as usable charge in the battery - this helper extends the charging time to account for that)
    * Helpers to set the departure time for each day of the week (plus whether or not the car will depart on each day)
    * Helpers to set if the car should be climatized before departure, and how long before departure the climatizing should start
    * Template sensor to combine all the departure and climatize helpers into a sensor
    * Automation to start climatizing<br>
  * For each charger, the packages contain:<br>
    * Helper for selecting which car is connected to the charger
    * Helper to set the maximum charging current (this is a workaround to limit the power drawn, as temporary replacement for load balancing - which I haven't had time to develop as of yet)
    * Helper to know whether charging has completed (charging goal reached - this is used to make sure the charger can deliver current even outside allowed charging hours; equivalent to "current at any time" setting in the Easee charger app)
    * Template sensor to combine relevant helpers (for car and charger) into a sensor (it makes the `elbillading` AppDaemon app simpler)
    * Template sensors, sensors, and utility_meters to monitor monthly energy and cost consumption by the charger (and to calculate monthly average charging energy price - useful if you want to compare your average hourly charging price with your average hourly electricity price for your home - how much did you save by smart charging?)
    * Automations to run the `elbillading` AppDaemon app whenever necessary and to start and stop charging

# Use
The AppDaemon apps should be good to go, although you will have to adapt the `apps.yaml` files to suit your Home Assistance instance (rename the sensor names, for example)

The `strompris` AppDaemon app adds the energy price (for me the spot price received from the [nordpool](https://github.com/custom-components/nordpool) integration) to the energy surcharge (0.01 NOK/kWh charged by my energy provider) and the grid tariff (which in my case is received from the [NettleieElvia](https://github.com/uphillbattle/NettleieElvia) AppDaemon app). You will have to provide the sensors and/or helpers for those three quantities.

For the `elbillading` AppDaemon app, you will have to specify the charger ID and the `strompris` sensor.

In the packages, you will have to change the sensor names for your car(s) and charger(s). If you only have one car and/or one charger, you will have to modify the `yaml` files accordingly. If you have other car or charger makes than BMW and/or Easee, you will have to adapt accordingly as sensor names and services are not likely to be the same.

Best of luck!

# Disclaimer
The material embodied in this software is provided to you "as-is" and without warranty of any kind, express, implied or otherwise, including without limitation, any warranty of fitness for a particular purpose. In no event shall [uphillbattle](https://github.com/uphillbattle) be liable to you or anyone else for any direct, special, incidental, indirect or consequential damages of any kind, or any damages whatsoever, including without limitation, loss of profit, loss of use, savings or revenue, or the claims of third parties, whether or not [uphillbattle](https://github.com/uphillbattle) has been advised of the possibility of such loss, however caused and on any theory of liability, arising out of or in connection with the possession, use or performance of this software.
