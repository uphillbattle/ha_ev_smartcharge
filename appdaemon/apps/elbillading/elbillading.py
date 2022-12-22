import appdaemon.plugins.hass.hassapi as hass
import datetime
import time
import math



class elbillading(hass.Hass):

  def initialize(self):
    self.days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    self.log_progress        = self.args["log_progress"]
    self.log_debug           = self.args["log_debug"]
    self.event_name          = self.args["charger_id"].lower() + "_connection"
    self.charger_id          = self.args["charger_id"].lower()
    self.setupEntitiesDone   = False
    self.run_in(self.setup_entities, 1)




  def setup_entities(self, kwargs):
    # Setup triggers:
      # listen_event created by yaml automation when:
        # When car is plugged in (charger_status)
        # When strompris changes (strompris_hjemme)
        # When any car charging parameters change or associated car changes (charger_car)
        # When smartcharging is switched on or off (input_boolean.charger_smart_charging)
    self.chargerCarEntitySet    = False
    self.chargerCarEntityName = "sensor." + self.charger_id + "_car"
    if self.entity_exists(self.chargerCarEntityName):
      self.chargerCarEntity       = self.get_entity(self.chargerCarEntityName)
      self.chargerCarEntitySet    = True

    self.energyPriceEntitySet   = False
    self.energyPriceEntityName  = self.args["energy_price"]
    if self.entity_exists(self.energyPriceEntityName):
      self.energyPriceEntity      = self.get_entity(self.energyPriceEntityName)
      self.energyPriceEntitySet   = True

    self.chargerSmartChargeEntitySet   = False
    self.chargerSmartChargeEntityName  = "switch." + self.charger_id + "_smart_charging"
    if self.entity_exists(self.chargerSmartChargeEntityName):
      self.chargerSmartChargeEntity      = self.get_entity(self.chargerSmartChargeEntityName)
      self.chargerSmartChargeEntitySet   = True

    self.chargerMaxCurrentEntitySet   = False
    self.chargerMaxCurrentEntityName  = "input_number." + self.charger_id + "_maximum_charging_current"
    if self.entity_exists(self.chargerMaxCurrentEntityName):
      self.chargerMaxCurrentEntity      = self.get_entity(self.chargerMaxCurrentEntityName)
      self.chargerMaxCurrentEntitySet   = True

    self.chargerStatusEntitySet = False
    self.chargerStatusEntityName = "sensor." + self.charger_id + "_status"
    if self.entity_exists(self.chargerStatusEntityName):
      self.chargerStatusEntity    = self.get_entity(self.chargerStatusEntityName)
      self.chargerStatusEntitySet = True

    self.setupEntitiesDone = (self.chargerCarEntitySet and 
                              self.energyPriceEntitySet and 
                              self.chargerSmartChargeEntitySet and 
                              self.chargerStatusEntitySet and
                              self.chargerMaxCurrentEntitySet)

    if self.setupEntitiesDone:
      self.listen_event(self.event_handling, self.event_name)
      if (self.log_progress):
        self.log("__function__: Setup done", log="main_log", level="INFO")
        self.log("__function__: {} = {}".format("self.event_name", self.event_name), log="main_log", level="INFO")
        self.log("__function__: Calling {}".format("event_handling"), log="main_log", level="INFO")
      self.event_handling("setup_entities", [])
      if (self.log_progress):
        self.log("__function__: {} complete".format("event_handling"), log="main_log", level="INFO")

    if not(self.setupEntitiesDone):
      self.run_in(self.setup_entities, 10)
      self.log("__function__: Re-calling setup", log="main_log", level="INFO")
      if (self.log_debug):
        self.log("__function__: {} = {}".format("self.chargerCarEntitySet", self.chargerCarEntitySet), log="main_log", level="INFO")
        self.log("__function__: {} = {}".format("self.energyPriceEntitySet", self.energyPriceEntitySet), log="main_log", level="INFO")
        self.log("__function__: {} = {}".format("self.chargerSmartChargeEntitySet", self.chargerSmartChargeEntitySet), log="main_log", level="INFO")
        self.log("__function__: {} = {}".format("self.chargerStatusEntitySet", self.chargerStatusEntitySet), log="main_log", level="INFO")
        self.log("__function__: {} = {}".format("self.chargerMaxCurrentEntityName", self.chargerMaxCurrentEntityName), log="main_log", level="INFO")
        self.log("__function__: {} = {}".format("self.chargerMaxCurrentEntitySet", self.chargerMaxCurrentEntitySet), log="main_log", level="INFO")




  def event_handling(self, event_name, data, *args, **kwargs):
    self.log("__function__: Event {} caught".format(event_name), log="main_log", level="INFO")
    self.fetch_data()
    self.find_next_departure()
    self.find_required_charging_time()
    self.find_charging_hours()
    self.set_output_sensor()


  def fetch_data(self):
    # Get the charging parameters of the car
    self.chargerCar         = self.chargerCarEntity.get_state(attribute="all")
    self.energyPrice        = self.energyPriceEntity.get_state(attribute="all")
    self.chargerSmartCharge = self.chargerSmartChargeEntity.get_state(attribute="all")
    self.chargerMaxCurrent  = self.chargerMaxCurrentEntity.get_state(attribute="all")
    self.chargerStatus      = self.chargerStatusEntity.get_state(attribute="all")

    self.carChargeLevel = self.chargerCar["attributes"]["remaining_battery_charge"]
    if self.carChargeLevel == 'unknown':
      self.carChargeLevel = 10
      self.log("__function__: {} is unknown, set to 10 %".format("Remaining battery charge"), log="main_log", level="WARNING")

    self.departures     = []
    self.departureTimes = []
    for day in self.days:
      self.departures.append('on' == self.chargerCar["attributes"]["departure_" + day])
      self.departureTimes.append(datetime.datetime.strptime(self.chargerCar["attributes"]["departure_time_" + day], '%H:%M:%S').time())
    self.today = datetime.datetime.now().weekday()
    self.currentHour = float(datetime.datetime.now().hour) + float(datetime.datetime.now().minute)/60.0

    if (self.log_debug):
      self.log("__function__: {} = {}".format(self.chargerCarEntityName, self.chargerCar["state"]), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format(self.energyPriceEntityName, self.energyPrice["state"]), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format(self.chargerSmartChargeEntityName, self.chargerSmartCharge["state"]), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format(self.chargerStatusEntityName, self.chargerStatus["state"]), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("self.departures", self.departures), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("self.departureTimes", self.departureTimes), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("self.today", self.today), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("self.currentHour", self.currentHour), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("self.departures[self.today]", self.departures[self.today]), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("self.departureTimes[self.today]", self.departureTimes[self.today]), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("self.departureTimes[self.today].hour", self.departureTimes[self.today].hour), log="main_log", level="INFO")




  def find_next_departure(self):
    # When is the car due to depart?
    departureToday = self.departures[self.today]
    if departureToday:
      departureTimeToday = (float(self.departureTimes[self.today].hour) + 
                            float(self.departureTimes[self.today].minute)/60.0)
      if departureTimeToday > self.currentHour:
        self.timeToDeparture = (float(self.departureTimes[self.today].hour) + 
                                float(self.departureTimes[self.today].minute - datetime.datetime.now().minute)/60.0 - 
                                float(datetime.datetime.now().hour))
        self.departureHourNumber = self.departureTimes[self.today].hour
      else:
        departureToday = False

    if not(departureToday):
      self.timeToDeparture = 24.0 - self.currentHour
      self.departureHourNumber = 24
      for i in range(7):
        if self.departures[(self.today + i + 1) % 7]:
          self.timeToDeparture = (self.timeToDeparture + 
                                  float(self.departureTimes[(self.today + i + 1) % 7].hour) + 
                                  float(self.departureTimes[(self.today + i + 1) % 7].minute)/60.0)
          self.departureHourNumber = self.departureHourNumber + self.departureTimes[(self.today + i + 1) % 7].hour
          break
        else:
          self.timeToDeparture = self.timeToDeparture + 24.0
          self.departureHourNumber = self.departureHourNumber + 24
    
    if (self.log_debug):
      self.log("__function__: {} = {}".format("self.timeToDeparture", self.timeToDeparture), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("self.departureHourNumber", self.departureHourNumber), log="main_log", level="INFO")




  def find_required_charging_time(self):
    # Calculate the needed charging time
    chargeLevel                 = float(self.carChargeLevel)
    chargeGoal                  = float(self.chargerCar["attributes"]["charging_goal"])
    minimumCharge               = float(self.chargerCar["attributes"]["minimum_charge"])
    batteryCapacity             = float(self.chargerCar["attributes"]["battery_capacity"])
    lossCompensation            = 1.0 + (float(self.chargerCar["attributes"]["charging_losses"])/100.0)
    requiredCharge              = max(chargeGoal - chargeLevel, 0.0)/100.0*batteryCapacity*lossCompensation
    requiredChargeToMinimum     = max(minimumCharge - chargeLevel, 0.0)/100.0*batteryCapacity*lossCompensation
    carMaximumChargePower       = float(self.chargerCar["attributes"]["maximum_charging_power"])
    chargerPhaseMode            = self.chargerStatus["attributes"]["config_phaseMode"]
    chargerCircuitRatedCurrent  = float(self.chargerStatus["attributes"]["circuit_ratedCurrent"])
    chargerMaxCurrent           = float(self.chargerMaxCurrent["state"])
    if chargerPhaseMode == 1: 
      chargerMaximumChargePower = float(round(chargerCircuitRatedCurrent*230.0/1000.0, 1))
      chargerMaxCurrentPower    = float(round(chargerMaxCurrent*230/1000.0, 1))
    else:
      chargerMaximumChargePower = float(round(chargerCircuitRatedCurrent*400.0*1.73205/1000.0, 0))
      chargerMaxCurrentPower    = float(round(chargerMaxCurrent*400*1.73205/1000.0, 0))
    maximumChargePower          = min(carMaximumChargePower, 
                                      chargerMaximumChargePower,
                                      chargerMaxCurrentPower)
    self.requiredChargeTime     = requiredCharge/maximumChargePower
    self.requiredChargeTimeToMinimum = requiredChargeToMinimum/maximumChargePower
    if (self.log_debug):
      self.log("__function__: {} = {}".format("requiredCharge", requiredCharge), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("requiredChargeToMinimum", requiredChargeToMinimum), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("maximumChargePower", maximumChargePower), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("self.requiredChargeTime", self.requiredChargeTime), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("self.requiredChargeTimeToMinimum", self.requiredChargeTimeToMinimum), log="main_log", level="INFO")




  def find_charging_hours(self):
    # Find the cheapest hours needed to charge the car in time
    cheapestHours = self.energyPrice["attributes"]["sorted_strompris"]
    availableHours = []
    availableHoursCount = 0
    currentHourNumber = int(self.currentHour)
    for element in cheapestHours:
      if (element["hour"] >= currentHourNumber) and (element["hour"] <= self.departureHourNumber):
        availableHours.append(element["hour"])
        availableHoursCount = availableHoursCount + 1
    if (self.log_debug):
      self.log("__function__: {} = {}".format("availableHours", availableHours), log="main_log", level="INFO")
    if (self.departureHourNumber in availableHours):
      # Departure is closer than the energyPrice horizon
      if (self.departureHourNumber == currentHourNumber):
        # Departure is within the current hour
        self.chargingHours = [currentHourNumber]
      elif (self.departureHourNumber == (currentHourNumber + 1)):
        # Departure is within the next hour
        self.chargingHours = availableHours
      else:
        requiredHours = max(min(math.ceil(self.requiredChargeTime), len(availableHours)), 1)
        self.chargingHours = availableHours[0:requiredHours]
        hoursPicked = requiredHours
        if (self.log_debug):
          self.log("__function__: {} = {}".format("requiredHours", requiredHours), log="main_log", level="INFO")
          self.log("__function__: {} = {}".format("availableHours", availableHours), log="main_log", level="INFO")
          self.log("__function__: {} = {}".format("self.chargingHours", self.chargingHours), log="main_log", level="INFO")
        if (self.departureHourNumber in self.chargingHours):
          if len(availableHours) > hoursPicked:
            self.chargingHours.append(availableHours[hoursPicked])
            hoursPicked = hoursPicked + 1
        if (self.log_debug):
          self.log("__function__: {} = {}".format("self.chargingHours", self.chargingHours), log="main_log", level="INFO")
          self.log("__function__: {} = {}".format("len(availableHours)", len(availableHours)), log="main_log", level="INFO")
        if (currentHourNumber in self.chargingHours):
          if len(availableHours) > hoursPicked:
            self.chargingHours.append(availableHours[hoursPicked])
        elif (self.requiredChargeTimeToMinimum > 0):
          self.chargingHours.append(currentHourNumber)
        if (self.log_debug):
          self.log("__function__: {} = {}".format("self.chargingHours", self.chargingHours), log="main_log", level="INFO")
    else:
      requiredHours = max(min(math.ceil(self.requiredChargeTime), len(availableHours)), 1)
      self.chargingHours = availableHours[0:requiredHours]
      hoursPicked = requiredHours
      if (self.log_debug):
        self.log("__function__: {} = {}".format("requiredHours", requiredHours), log="main_log", level="INFO")
        self.log("__function__: {} = {}".format("availableHours", availableHours), log="main_log", level="INFO")
        self.log("__function__: {} = {}".format("self.chargingHours", self.chargingHours), log="main_log", level="INFO")
      if (self.departureHourNumber in self.chargingHours):
        if len(availableHours) > hoursPicked:
          self.chargingHours.append(availableHours[hoursPicked])
          hoursPicked = hoursPicked + 1
      if (self.log_debug):
        self.log("__function__: {} = {}".format("self.chargingHours", self.chargingHours), log="main_log", level="INFO")
        self.log("__function__: {} = {}".format("len(availableHours)", len(availableHours)), log="main_log", level="INFO")
      if (currentHourNumber in self.chargingHours):
        if len(availableHours) > hoursPicked:
          self.chargingHours.append(availableHours[hoursPicked])
      elif (self.requiredChargeTimeToMinimum > 0):
        self.chargingHours.append(currentHourNumber)
      if (self.log_debug):
        self.log("__function__: {} = {}".format("self.chargingHours", self.chargingHours), log="main_log", level="INFO")
    if len(self.chargingHours) > 1:
      self.chargingHours.sort()

    if (self.log_debug):
      self.log("__function__: {} = {}".format("self.departureHourNumber", self.departureHourNumber), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("availableHours", availableHours), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("self.chargingHours", self.chargingHours), log="main_log", level="INFO")



  def set_output_sensor(self):
    sensorName = "binary_sensor." + self.charger_id + "_charging_control"
    friendlyName = self.charger_id.upper() + " smart charge"
    smartChargeEnabled = self.chargerSmartCharge["state"]
    self.set_state(sensorName,
                   state=smartChargeEnabled,
                   attributes={'friendly_name': friendlyName, 
                               'icon': 'mdi:auto-fix',
                               'charging_hours': self.chargingHours,
                               'last_updated': int(time.time()),
                               'last_updated_date_time': datetime.datetime.now()})
    if (self.log_progress):
      self.log("__function__: {} = {}".format(sensorName, smartChargeEnabled), log="main_log", level="INFO")
      self.log("__function__: {} = {}".format("charging_hours", self.chargingHours), log="main_log", level="INFO")
