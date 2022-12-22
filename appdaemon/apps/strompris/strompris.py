import appdaemon.plugins.hass.hassapi as hass
import requests
import json
import datetime
import time




class strompris(hass.Hass):

  def initialize(self):
    self.log_progress  = (self.args["log_progress"])
    self.listenersSet = False
    self.energyPrice = 0.0
    self.energySurcharge = 0.0
    self.gridTariff = 0.0
    self.run_in(self.setup_listeners, 1)


  def setup_listeners(self, kwargs):
    self.strompris = 0.0
    self.energyPriceListenerSet     = False
    self.energySurchargeListenerSet = False
    self.gridTariffListenerSet      = False

    if self.entity_exists(self.args["energyPrice"]):
      self.energyPriceEntity = self.get_entity(self.args["energyPrice"])
      self.energyPrice = self.energyPriceEntity.get_state(attribute="all")
      self.log("__function__: {} = {} kr/kWh".format(self.args["energyPrice"], self.energyPrice["state"]), log="main_log", level="INFO")
      #self.log("__function__: {} = {} ".format("len(" + self.args["energyPrice"] + "['attributes']['raw_tomorrow'])", len(self.energyPrice["attributes"]["raw_tomorrow"])), log="main_log", level="INFO")
      self.strompris = float(self.energyPrice["state"])
      self.energyPriceListenerSet = True 

    if self.entity_exists(self.args["energySurcharge"]):
      self.energySurchargeEntity = self.get_entity(self.args["energySurcharge"])
      self.energySurcharge = self.energySurchargeEntity.get_state(attribute="all")
      self.log("__function__: {} = {} kr/kWh".format(self.args["energySurcharge"], float(self.energySurcharge["state"])/100.0), log="main_log", level="INFO")
      self.strompris = self.strompris + float(self.energySurcharge["state"])/100.0
      self.energySurchargeListenerSet = True

    if self.entity_exists(self.args["gridTariff"]):
      self.gridTariffEntity = self.get_entity(self.args["gridTariff"])
      self.gridTariff = self.gridTariffEntity.get_state(attribute="all")
      self.log("__function__: {} = {} kr/kWh".format(self.args["gridTariff"], float(self.gridTariff["state"])), log="main_log", level="INFO")
      self.strompris = round(self.strompris + float(self.gridTariff["state"]), 4)
      self.log("__function__: Strompris = {} kr/kWh".format(self.strompris), log="main_log", level="INFO")
      self.gridTariffListenerSet      = True 

    self.ListenersAnd = (self.energyPriceListenerSet and self.energySurchargeListenerSet and self.gridTariffListenerSet)
    self.ListenersOr  = (self.energyPriceListenerSet or  self.energySurchargeListenerSet or  self.gridTariffListenerSet)
    if (self.ListenersOr):
      self.set_state(self.args["sensorname"], \
                    state=self.strompris, \
                    attributes={'friendly_name': self.args["sensoralias"], \
                                'unit_of_measurement': 'NOK/kWh', \
                                'icon': 'mdi:currency-usd'})      
    if (self.ListenersAnd):
      self.listen_state(self.on_listen, self.args["energyPrice"], attribute="all")
      self.listen_state(self.on_listen, self.args["energySurcharge"])
      self.listen_state(self.on_listen, self.args["gridTariff"], attribute="all")
      self.listenersSet = True
      self.run_in(self.updateStrompris, 1)
    if not(self.listenersSet):
      self.run_in(self.setup_listeners, 10)



  def on_listen(self, entity, attribute, old, new, kwargs):
    self.run_in(self.updateStrompris, 1)



  def updateStrompris(self, kwargs):
    self.energyPrice = self.energyPriceEntity.get_state(attribute="all")
    self.energySurcharge = float(self.get_state(self.args["energySurcharge"]))/100.0
    self.gridTariff = self.gridTariffEntity.get_state(attribute="all")

    try:
      self.strompris = round(float(self.energyPrice["state"]) + self.energySurcharge + float(self.gridTariff["state"]), 4)
    except Exception as e:
      self.log("__function__: Could not calculate strompris\n{}".format(e), log="main_log", level="WARNING")
      return None

    self.stromprisRaw = []
    self.stromprisList = []
    self.stromprisTodayRaw = []
    self.stromprisTodayList = []
    self.stromprisTomorrowRaw = []
    self.stromprisTomorrowList = []
    self.hourNumber = 0
    self.offpeak1sum = 0
    self.offpeak1count = 0
    self.offpeak1today = 0
    self.offpeak1tomorrow = []
    self.offpeak2sum = 0
    self.offpeak2count = 0
    self.offpeak2today = 0
    self.offpeak2tomorrow = []
    self.peaksum = 0
    self.peakcount = 0
    self.peaktoday = 0
    self.peaktomorrow = []
    self.todaysum = 0
    self.todaycount = 0
    self.today = 0
    self.tomorrowsum = 0
    self.tomorrowcount = 0
    self.tomorrow = []
    self.minimumtoday = []
    self.minimumtomorrow = []
    self.maximumtoday = []
    self.maximumtomorrow = []
    try:
      if (len(self.energyPrice["attributes"]["raw_today"]) == len(self.gridTariff["attributes"]["raw_today"])):
        for index in range(len(self.energyPrice["attributes"]["raw_today"])):
          startTime   = self.energyPrice["attributes"]["raw_today"][index]["start"]
          endTime     = self.energyPrice["attributes"]["raw_today"][index]["end"]
          energyPrice = float(self.energyPrice["attributes"]["raw_today"][index]["value"])
          gridTariff  = float(self.gridTariff["attributes"]["raw_today"][index]["value"])
          strompris   = round(energyPrice + self.energySurcharge + gridTariff, 4)
          self.stromprisRaw.append({"start": startTime, "end": endTime, "hour": self.hourNumber, "value": strompris})
          self.stromprisTodayRaw.append({"start": startTime, "end": endTime, "hour": self.hourNumber, "value": strompris})
          self.stromprisList.append(strompris)
          self.stromprisTodayList.append(strompris)
          self.todaysum = self.todaysum + strompris
          self.todaycount = self.todaycount + 1
          if self.hourNumber < 8:
            self.offpeak1sum = self.offpeak1sum + strompris
            self.offpeak1count = self.offpeak1count + 1
          elif self.hourNumber < 20:
            self.peaksum = self.peaksum + strompris
            self.peakcount = self.peakcount + 1
          else:
            self.offpeak2sum = self.offpeak2sum + strompris
            self.offpeak2count = self.offpeak2count + 1
          if self.hourNumber == 0:
            self.minimumtoday = strompris
            self.maximumtoday = strompris
          else:
            if strompris < self.minimumtoday:
              self.minimumtoday = strompris
            if strompris > self.maximumtoday:
              self.maximumtoday = strompris
          self.hourNumber = self.hourNumber + 1
        if self.todaycount > 0:
          self.today = self.todaysum/self.todaycount
          self.nowtotoday = self.strompris/self.today
        if self.offpeak1count > 0:
          self.offpeak1today = self.offpeak1sum/self.offpeak1count
        if self.offpeak2count > 0:
          self.offpeak2today = self.offpeak2sum/self.offpeak2count
        if self.peakcount > 0:
          self.peaktoday = self.peaksum/self.peakcount
    except Exception as e:
      self.log("__function__: Could not set stromprisRaw today\n{}".format(e), log="main_log", level="WARNING")

    self.tomorrow_valid = False
    try:
      if (self.energyPrice["attributes"]["tomorrow_valid"] and (datetime.datetime.now().hour >= 13)):
        if ((len(self.energyPrice["attributes"]["raw_tomorrow"]) == len(self.gridTariff["attributes"]["raw_tomorrow"])) and
            (len(self.energyPrice["attributes"]["raw_tomorrow"]) > 0)):
          for index in range(len(self.energyPrice["attributes"]["raw_tomorrow"])):
            startTime   = self.energyPrice["attributes"]["raw_tomorrow"][index]["start"]
            endTime     = self.energyPrice["attributes"]["raw_tomorrow"][index]["end"]
            gridTariff  = float(self.gridTariff["attributes"]["raw_tomorrow"][index]["value"])
            energyPrice = self.energyPrice["attributes"]["raw_tomorrow"][index]["value"]
            if not(energyPrice is None):
              self.tomorrow_valid = True
              energyPrice = float(energyPrice)
              strompris   = round(energyPrice + self.energySurcharge + gridTariff, 4)
              self.stromprisRaw.append({"start": startTime, "end": endTime, "hour": self.hourNumber, "value": strompris})
              self.stromprisTomorrowRaw.append({"start": startTime, "end": endTime, "hour": self.hourNumber, "value": strompris})
              self.stromprisList.append(strompris)
              self.stromprisTomorrowList.append(strompris)
              self.tomorrowsum = self.tomorrowsum + strompris
              self.tomorrowcount = self.tomorrowcount + 1
              if self.hourNumber < 32:
                self.offpeak1sum = self.offpeak1sum + strompris
                self.offpeak1count = self.offpeak1count + 1
              elif self.hourNumber < 44:
                self.peaksum = self.peaksum + strompris
                self.peakcount = self.peakcount + 1
              else:
                self.offpeak2sum = self.offpeak2sum + strompris
                self.offpeak2count = self.offpeak2count + 1
              if self.hourNumber == 24:
                self.minimumtomorrow = strompris
                self.maximumtomorrow = strompris
              else:
                if strompris < self.minimumtomorrow:
                  self.minimumtomorrow = strompris
                if strompris > self.maximumtomorrow:
                  self.maximumtomorrow = strompris
              self.hourNumber = self.hourNumber + 1
            if self.tomorrowcount > 0:
              self.tomorrow = self.tomorrowsum/self.tomorrowcount
            if self.offpeak1count > 0:
              self.offpeak1tomorrow = self.offpeak1sum/self.offpeak1count
            if self.offpeak2count > 0:
              self.offpeak2tomorrow = self.offpeak2sum/self.offpeak2count
            if self.peakcount > 0:
              self.peaktomorrow = self.peaksum/self.peakcount
    except Exception as e:
      self.log("__function__: Could not set stromprisRaw tomorrow\n{}".format(e), log="main_log", level="WARNING")

    self.stromprisRawSorted = sorted(self.stromprisRaw, key=lambda s: s['value'])

    self.set_state(self.args["sensorname"], \
                   state=self.strompris, \
                   attributes={'friendly_name': self.args["sensoralias"], \
                               'unit_of_measurement': 'NOK/kWh', \
                               'icon': 'mdi:currency-usd', \
                               'current_price': self.strompris, \
                               'ratio_current_to_average_today': self.nowtotoday, \
                               'offpeak1_today': self.offpeak1today, \
                               'offpeak2_today': self.offpeak2today, \
                               'peak_today': self.peaktoday, 
                               'minimum_today': self.minimumtoday, \
                               'maximum_today': self.maximumtoday, \
                               'average_today': self.today, \
                               'offpeak1_tomorrow': self.offpeak1tomorrow, \
                               'offpeak2_tomorrow': self.offpeak2tomorrow, \
                               'peak_tomorrow': self.peaktomorrow, \
                               'minimum_tomorrow': self.minimumtomorrow, \
                               'maximum_tomorrow': self.maximumtomorrow, \
                               'average_tomorrow': self.tomorrow, \
                               'tomorrow_valid': self.tomorrow_valid, \
                               'strompris': self.stromprisList, \
                               'strompris_today': self.stromprisTodayList, \
                               'strompris_tomorrow': self.stromprisTomorrowList, \
                               'raw_strompris': self.stromprisRaw, \
                               'raw_strompris_today': self.stromprisTodayRaw, \
                               'raw_strompris_tomorrow': self.stromprisTomorrowRaw, \
                               'sorted_strompris': self.stromprisRawSorted})
    self.log("__function__: Strompris = {} kr/kWh".format(self.strompris), log="main_log", level="INFO")
