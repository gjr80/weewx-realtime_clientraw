# rtcr.py
#
# A weeWX service to generate a loop based clientraw.txt to support the
# Saratoga Weather Web Templates dashboards.
#
# Copyright (C) 2017 Gary Roderick                  gjroderick<at>gmail.com
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see http://www.gnu.org/licenses/.
#
# Version: 0.2.0                                        Date: 19 March 2017
# Version: 0.2.1                                        Date: ?? March 2017
#
# Revision History
#                       v0.2.1  - clientraw.txt content can now be sent to a
#                                 remote URL via HTTP POST.
#                               - day windrun calculations are now seeded on
#                                 startup
#                               - field 117 average wind direction now
#                                 calculated (assumed to be average direction
#                                 over the current day)
#   19 March 2017       v0.2.0  - added trend period config options, reworked
#                                 trend field calculations
#                               - buffer object is now seeded on startup
#                               - added support for 9am rain reset total
#                               - binding used for appTemp data is now set
#                                 by additional_binding config option
#                               - added comments details supported fields as
#                                 well as fields required by Saratoga dashboard
#                                 and Alternative dashboard
#                               - now calculates maxSolarRad if pyphem is
#                                 present
#                               - maxSolarRad algorithm now selectable through
#                                 config options
#                               - removed a number of unused buffer object
#                                 properties
#   3 March 2017        v0.1.0  - initial release
#

"""The RealtimeClientraw service generates a loop based clientraw.txt that can
be used to update the Saratoga Weather Web Templates dashboard and the
Alternative dashboard in near real time.

Whilst the RealtimeClientraw generated
clientraw.txt will is fully compatible with the Saratoga dashboard and the
Alternative dashboard, some of the other uses of clientraw.txt are not fully
supported. For example, clientraw.txt can also be used as a data feed for
Weather Display Live (WDL); however, a number of the fields used by WDL are not
populated by the RealtimeClientraw service. Other applications of clientraw.txt
may or may not be supported by the RealtimeClientraw generated clientraw.txt
depending on what clientraw.txt fields are used.

A list showing which clientraw.txt fields are/are not populated by the R
ealtimeClientraw service is included below.

Inspired by crt.py v0.5 by Matthew Wall, a weeWX service to emit loop data to
file in Cumulus realtime format. Refer http://wiki.sandaysoft.com/a/Realtime.txt

Abbreviated instructions for use:

1.  Put this file in $BIN_ROOT/user.

2.  Add the following stanza to weewx.conf:

[RealtimeClientraw]
    # Path to clientraw.txt. Relative paths are relative to HTML_ROOT. If
    # empty default is HTML_ROOT. If setting omitted altogether default is
    # /var/tmp
    rtcr_path = /home/weewx/public_html

    # Minimum interval (seconds) between file generation. Ideally
    # clientraw.txt would be generated on receipt of every loop packet (there
    # is no point in generating more frequently than this); however, in some
    # cases the user may wish to generate clientraw.txt less frequently. The
    # min_interval option sets the minimum time between successive
    # clientraw.txt generations. Generation will be skipped on arrival of a
    # loop packet if min_interval seconds have NOT elapsed since the last
    # generation. If min_interval is 0 or omitted generation will occur on
    # every loop packet (as will be the case if min_interval < station loop
    period). Optional, default is 0.
    min_interval =

    # Binding to use for appTemp data. Optional, default None.
    additional_binding = None

    # Update windrun value each loop period or just on each archive period.
    # Optional, default is False.
    windrun_loop = false

    # Stations that provide partial packets are supported through a cache that
    # caches packet data. max_cache_age is the maximum age  in seconds for
    # which cached data is retained. Optional, default is 600 seconds.
    max_cache_age = 600

    avgspeed_period = 300
    gust_period = 300

    # Period in seconds over which to calculate trends. Anecdotally,
    # clientraw.txt appears to use 1 hour for each but barometer trends are
    # commonly calculated over a 3 hour period. Optional, default is 3600.
    baro_trend_period = 3600
    temp_trend_period = 3600
    humidity_trend_period = 3600
    humidex_trend_period = 3600

    # Largest acceptable diffference in seconds between ... when searchin ghte archive. Optional, default is 200.
    grace = 200

4.  Add the RealtimeClientraw service to the list of report services under
[Engines] [[WxEngine]] in weewx.conf:

[Engines]
    [[WxEngine]]
        report_services = ..., user.rtcr.RealtimeClientraw

5.  Stop/start weeWX

6.  Confirm that clientraw.txt is being generated regularly as per the
    min_interval setting under [RealtimeClientraw] in weewx.conf.

To do:
    - seed RtcrBuffer day stats properties with values from daily summaries on
      startup

Fields to implemented/finalised:
    - 015 - forecast icon.
    - *048 - icon type.
    - *049 - weather description.
    - *090 - temperature 1 hour ago.
    - *113 - maximum average speed. What is the definition? Over what period?
    - 133 - maximum windGust last hour. Is it even used? Might not implement.
    - 134 - maximum windGust in last hour time. Refer 133.
    - #173 - day windrun.

Saratoga Dashboard
    - fields required:
        0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 19, 29, 30, 31, 32, 34, 35, 36, 44,
        45, 46, 47, 48, 49, 50, 71, 72, 73, 74, 75, 76, 77, 78, 79, 90, 110,
        111, 112, 113, 127, 130, 131, 132, 135, 136, 137, 138, 139, 140, 141
    - fields to be implemented/finalised in order to support:
        48, 49, 90, 113

Alternative Dashboard
    - fields required (Saratoga fields plus)(#=will not implememnt):
        1, 12, 13, #114, #115, #116, #118, #119, 156, 159, 160, 173
    - fields to be implemented/finalised in order to support:
        48, 49, 90, 113, 114, 115, 116, 118, 119, 173
"""

# python imports
import Queue
import datetime
import httplib
import math
import os.path
import socket
import sys
import syslog
import threading
import time
import urllib2

from operator import itemgetter

# weeWX imports
import weedb
import weewx
import weeutil.weeutil
import weewx.units
import weewx.wxformulas
from weewx.engine import StdService
from weewx.units import ValueTuple, convert, getStandardUnitType, ListOfDicts
from weeutil.weeutil import to_bool, to_int

# version number of this script
RTCR_VERSION = '0.2.1'

# the obs that we will buffer
MANIFEST = ['outTemp', 'barometer', 'outHumidity', 'rain', 'rainRate',
            'humidex', 'windchill', 'heatindex', 'windSpeed', 'inTemp',
            'appTemp', 'dewpoint', 'windDir', 'wind']
# obs for which we need hi/lo data
HILO_MANIFEST = ['outTemp', 'barometer', 'outHumidity',
                 'humidex', 'windchill', 'heatindex', 'windSpeed', 'inTemp',
                 'appTemp', 'dewpoint']
# obs for which we need a history
HIST_MANIFEST = ['windSpeed', 'windDir']
# obs for which we need a running sum
SUM_MANIFEST = ['rain']
MAX_AGE = 600
DEFAULT_MAX_CACHE_AGE = 600
DEFAULT_AVGSPEED_PERIOD = 300
DEFAULT_GUST_PERIOD = 300
DEFAULT_GRACE = 200
DEFAULT_TREND_PERIOD = 3600


def logmsg(level, msg):
    syslog.syslog(level, msg)


def logcrit(id, msg):
    logmsg(syslog.LOG_CRIT, '%s: %s' % (id, msg))


def logdbg(id, msg):
    logmsg(syslog.LOG_DEBUG, '%s: %s' % (id, msg))


def logdbg2(id, msg):
    if weewx.debug >= 2:
        logmsg(syslog.LOG_DEBUG, '%s: %s' % (id, msg))


def loginf(id, msg):
    logmsg(syslog.LOG_INFO, '%s: %s' % (id, msg))


def logerr(id, msg):
    logmsg(syslog.LOG_ERR, '%s: %s' % (id, msg))


# ============================================================================
#                          class RealtimeClientraw
# ============================================================================


class RealtimeClientraw(StdService):
    """Service that generates clientraw.txt in near realtime.

    The RealtimeClientraw class creates and controls a threaded object of class
    RealtimeClientrawThread that generates clientraw.txt. Class
    RealtimeClientraw feeds the RealtimeClientrawThread object with data via an
    instance of Queue.Queue.
    """

    def __init__(self, engine, config_dict):
        # initialize my superclass
        super(RealtimeClientraw, self).__init__(engine, config_dict)

        # our queue
        self.rtcr_queue = Queue.Queue()

        # get a db manager object
        manager_dict = weewx.manager.get_manager_dict_from_config(config_dict,
                                                                  'wx_binding')
        self.db_manager = weewx.manager.open_manager(manager_dict)

        # get an instance of class RealtimeClientrawThread and start the thread
        # running
        self.rtcr_thread = RealtimeClientrawThread(self.rtcr_queue,
                                                   config_dict,
                                                   manager_dict,
                                                   location=engine.stn_info.location,
                                                   latitude=engine.stn_info.latitude_f,
                                                   longitude=engine.stn_info.longitude_f,
                                                   altitude=convert(engine.stn_info.altitude_vt, 'meter').value)
        self.rtcr_thread.start()

        # forecast and current condtions fields
        rtcr_config_dict = config_dict.get('RealtimeClientraw', {})
        self.forecast_binding = rtcr_config_dict.get('forecast_binding', None)
        if self.forecast_binding:
            try:
                self.forecast_manager = weewx.manager.open_manager_with_config(config_dict,
                                                                               self.forecast_binding)
            except weewx.UnknownBinding:
                self.forecast_manager = None
            if self.forecast_binding:
                self.forecast_text_field = rtcr_config_dict.get('forecast_text_field', None)
                self.forecast_icon_field = rtcr_config_dict.get('forecast_icon_field', None)
                self.current_text_field = rtcr_config_dict.get('current_text_field', None)

        # bind ourself to the relevant weeWX events
        self.bind(weewx.NEW_LOOP_PACKET, self.new_loop_packet)
        self.bind(weewx.NEW_ARCHIVE_RECORD, self.new_archive_record)
        self.bind(weewx.END_ARCHIVE_PERIOD, self.end_archive_period)

    def new_loop_packet(self, event):
        """Puts new loop packets in the rtcr queue."""

        # package the loop packet in a dict since this is not the only data
        # we send via the queue
        _package = {'type': 'loop',
                    'payload': event.packet}
        self.rtcr_queue.put(_package)
        logdbg2("rtcr", "queued loop packet: %s" %  _package['payload'])

    def new_archive_record(self, event):
        """Puts archive records in the rtcr queue."""

        # package the archive record in a dict since this is not the only data
        # we send via the queue
        _package = {'type': 'archive',
                    'payload': event.record}
        self.rtcr_queue.put(_package)
        logdbg2("rtcr", "queued archive record: %s" %  _package['payload'])
        # get yesterdays rainfall and put in the queue
        _rain_data = self.get_historical_rain(event.record['dateTime'])
        # package the data in a dict since this is not the only data we send
        # via the queue
        _package = {'type': 'stats',
                    'payload': _rain_data}
        self.rtcr_queue.put(_package)
        logdbg2("rtcr",
                "queued historical rainfall data: %s" %  _package['payload'])
        # get max gust in the last hour and put in the queue
        _hour_gust = self.get_hour_gust(event.record['dateTime'])
        # package the data in a dict since this is not the only data we send
        # via the queue
        _package = {'type': 'stats',
                    'payload': _hour_gust}
        self.rtcr_queue.put(_package)
        logdbg2("rtcr",
                "queued last hour gust: %s" %  _package['payload'])

    def end_archive_period(self, event):
        """Puts END_ARCHIVE_PERIOD event in the rtcr queue."""

        # package the event in a dict since this is not the only data we send
        # via the queue
        _package = {'type': 'event',
                    'payload': weewx.END_ARCHIVE_PERIOD}
        self.rtcr_queue.put(_package)
        logdbg2("rtcr", "queued weewx.END_ARCHIVE_PERIOD event")

    def shutDown(self):
        """Shut down any threads."""

        if hasattr(self, 'rtcr_queue') and hasattr(self, 'rtcr_thread'):
            if self.rtcr_queue and self.rtcr_thread.isAlive():
                # Put a None in the rtcr_queue to signal the thread to shutdown
                self.rtcr_queue.put(None)
                # Wait up to 20 seconds for the thread to exit:
                self.rtcr_thread.join(20.0)
                if self.rtcr_thread.isAlive():
                    logerr("rtcr", "Unable to shut down %s thread" % self.rtcr_thread.name)
                else:
                    logdbg("rtcr", "Shut down %s thread." % self.rtcr_thread.name)

    def get_minmax_obs(self, obs_type):
        """Obtain the alltime max/min values for an observation."""

        # create an interpolation dict
        inter_dict = {'table_name': self.db_manager.table_name,
                      'obs_type': obs_type}
        # the query to be used
        minmax_sql = "SELECT MIN(min), MAX(max) FROM %(table_name)s_day_%(obs_type)s"
        # execute the query
        _row = self.db_manager.getSql(minmax_sql % inter_dict)
        if not _row or None in _row:
            return {'min_%s' % obs_type: None,
                    'max_%s' % obs_type: None}
        else:
            return {'min_%s' % obs_type: _row[0],
                    'max_%s' % obs_type: _row[1]}

    def get_forecast(self):
        """Obtain the forecast and current conditions info."""

        if self.forecast_manager:
            manifest = [self.forecast_text_field,
                        self.forecast_icon_field,
                        self.current_text_field]
            fields = [a for a in manifest if a is not None]
            if len (fields) > 0:
                result = {}
                field_str = ','.join(fields)
                # create an interpolation dict
                inter_dict = {'table_name': self.forecast_manager.table_name,
                              'fields': field_str}
                # the query to be used
                _sql = "SELECT %(fields)s FROM %(table_name)s "\
                           "ORDER BY dateTime DESC LIMIT 1"
                # execute the query
                _row = self.db_manager.getSql(_sql % inter_dict)
                if not _row or None in _row:
                    for num in range(len(fields)):
                        result[fields[num]] = None
                else:
                    for num in range(len(fields)):
                        result[fields[num]] = _row[num]
            else:
                result = None
        else:
            result = None
        return result

    def get_historical_rain(self, ts):
        """Obtain yestredays total rainfall and return as a ValueTuple."""

        result = {}
        (unit, group) = weewx.units.getStandardUnitType(self.db_manager.std_unit_system,
                                                        'rain',
                                                        agg_type='sum')
        # Yesterday's rain
        # get a TimeSpan object for yesterdays archive day
        yest_tspan = weeutil.weeutil.archiveDaysAgoSpan(ts, days_ago=1)
        # create an interpolation dict
        inter_dict = {'table_name': self.db_manager.table_name,
                      'start': yest_tspan.start,
                      'stop': yest_tspan.stop}
        # the query to be used
        _sql = "SELECT SUM(rain) FROM %(table_name)s "\
                   "WHERE dateTime > %(start)s AND dateTime <= %(stop)s"
        # execute the query
        _row = self.db_manager.getSql(_sql % inter_dict)
        if not _row or None in _row:
            result['yest_rain_vt'] = ValueTuple(0.0, unit, group)
        else:
            result['yest_rain_vt'] = ValueTuple(_row[0], unit, group)

        # This month's rain
        # get a TimeSpan object for this month
        month_tspan = weeutil.weeutil.archiveMonthSpan(ts)
        # create an interpolation dict
        inter_dict = {'table_name': self.db_manager.table_name,
                      'start': yest_tspan.start,
                      'stop': yest_tspan.stop}
        # the query to be used
        _sql = "SELECT SUM(sum) FROM %(table_name)s_day_rain "\
                   "WHERE dateTime >= %(start)s AND dateTime < %(stop)s"
        # execute the query
        _row = self.db_manager.getSql(_sql % inter_dict)
        if not _row or None in _row:
            result['month_rain_vt'] = ValueTuple(0.0, unit, group)
        else:
            result['month_rain_vt'] = ValueTuple(_row[0], unit, group)

        # This year's rain
        # get a TimeSpan object for this year
        month_tspan = weeutil.weeutil.archiveYearSpan(ts)
        # create an interpolation dict
        inter_dict = {'table_name': self.db_manager.table_name,
                      'start': yest_tspan.start,
                      'stop': yest_tspan.stop}
        # the query to be used
        _sql = "SELECT SUM(sum) FROM %(table_name)s_day_rain "\
                   "WHERE dateTime >= %(start)s AND dateTime < %(stop)s"
        # execute the query
        _row = self.db_manager.getSql(_sql % inter_dict)
        if not _row or None in _row:
            result['year_rain_vt'] = ValueTuple(0.0, unit, group)
        else:
            result['year_rain_vt'] = ValueTuple(_row[0], unit, group)

        return result

    def get_hour_gust(self, ts):
        """Obtain the max wind gust in the last hour."""

        result = {}
        (unit, group) = weewx.units.getStandardUnitType(self.db_manager.std_unit_system,
                                                        'windGust')
        # get a TimeSpan object for the last hour
        hour_tspan = weeutil.weeutil.archiveSpanSpan(ts, hour_delta=1)
        # create an interpolation dict
        inter_dict = {'table_name': self.db_manager.table_name,
                      'start': hour_tspan.start,
                      'stop': hour_tspan.stop}
        # the query to be used
        _sql = "SELECT MAX(windGust) FROM %(table_name)s "\
                   "WHERE dateTime > %(start)s AND dateTime <= %(stop)s"
        # execute the query
        _row = self.db_manager.getSql(_sql % inter_dict)
        if not _row or None in _row:
            result['hour_gust_vt'] = ValueTuple(None, None, None)
        else:
            result['hour_gust_vt'] = ValueTuple(_row[0], unit, group)
        return result


# ============================================================================
#                       class RealtimeClientrawThread
# ============================================================================


class RealtimeClientrawThread(threading.Thread):
    """Thread that generates clientraw.txt in near realtime."""

    def __init__(self, queue, config_dict, manager_dict,
                 location, latitude, longitude, altitude):
        # Initialize my superclass:
        threading.Thread.__init__(self)

        self.setDaemon(True)
        self.rtcr_queue = queue
        self.config_dict = config_dict
        self.manager_dict = manager_dict

        # get our RealtimeClientraw config dictionary
        rtcr_config_dict = config_dict.get('RealtimeClientraw', {})

        # setup file generation timing
        self.min_interval = rtcr_config_dict.get('min_interval', None)
        self.last_write = 0 # ts (actual) of last generation

        # get our file paths and names
        _path = rtcr_config_dict.get('rtcr_path', '/var/tmp')
        _html_root = os.path.join(config_dict['WEEWX_ROOT'],
                                  config_dict['StdReport'].get('HTML_ROOT', ''))

        rtcr_path = os.path.join(_html_root, _path)
        self.rtcr_path_file = os.path.join(rtcr_path,
                                           rtcr_config_dict.get('rtcr_file_name',
                                                                'clientraw.txt'))

        # get the remote server URL if it exists, if it doesn't set it to None
        self.remote_server_url = rtcr_config_dict.get('remote_server_url', None)
        # timeout to be used for remote URL posts
        self.timeout = to_int(rtcr_config_dict.get('timeout', 2))
        # response text from remote URL if post was successful
        self.response = rtcr_config_dict.get('response_text', None)

        # some field definition settigns (mainly time periods for averages etc)
        self.avgspeed_period = rtcr_config_dict.get('avgspeed_period',
                                                    DEFAULT_AVGSPEED_PERIOD)
        self.gust_period = rtcr_config_dict.get('gust_period',
                                                DEFAULT_GUST_PERIOD)

        # set some format strings
        self.time_format = '%H:%M'
        self.flag_format = '%.0f'

        # get max cache age
        self.max_cache_age = to_int(rtcr_config_dict.get('max_cache_age',
                                                         DEFAULT_MAX_CACHE_AGE))

        # grace
        self.grace = to_int(rtcr_config_dict.get('grace', DEFAULT_GRACE))

        # Are we updating windrun using archive data only or archive and loop
        # data?
        self.windrun_loop = to_bool(rtcr_config_dict.get('windrun_loop',
                                                         'False'))

        # weeWX does not normally archive appTemp so day stats are not usually
        # available; however, if the user does have appTemp in a database then
        # if we have a binding we can use it. Check if an appTemp binding was
        # specified, if so use it, otherwise default to 'wx_binding'. We will
        # check for data existence before using it.
        self.additional_binding = rtcr_config_dict.get('additional_binding', None)

        # initialise day_oy_year property so when know when it's a new day
        self.dow = None

        # initialise some properties used to hold archive period wind data
        self.min_barometer = None
        self.max_barometer = None

        # get some station info
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.altitude_m = altitude
        self.station_type = config_dict['Station']['station_type']

        # extra sensors
        extra_sensor_config_dict = rtcr_config_dict.get('ExtraSensors', {})
        # temperature
        self.extra_temp1 = extra_sensor_config_dict.get('extraTemp1', None)
        self.extra_temp2 = extra_sensor_config_dict.get('extraTemp2', None)
        self.extra_temp3 = extra_sensor_config_dict.get('extraTemp3', None)
        self.extra_temp4 = extra_sensor_config_dict.get('extraTemp4', None)
        self.extra_temp5 = extra_sensor_config_dict.get('extraTemp5', None)
        self.extra_temp6 = extra_sensor_config_dict.get('extraTemp6', None)
        self.extra_temp7 = extra_sensor_config_dict.get('extraTemp7', None)
        self.extra_temp8 = extra_sensor_config_dict.get('extraTemp8', None)
        # humidity
        self.extra_hum1 = extra_sensor_config_dict.get('extraHumidity1', None)
        self.extra_hum2 = extra_sensor_config_dict.get('extraHumidity2', None)
        self.extra_hum3 = extra_sensor_config_dict.get('extraHumidity3', None)
        self.extra_hum4 = extra_sensor_config_dict.get('extraHumidity4', None)
        self.extra_hum5 = extra_sensor_config_dict.get('extraHumidity5', None)
        self.extra_hum6 = extra_sensor_config_dict.get('extraHumidity6', None)
        self.extra_hum7 = extra_sensor_config_dict.get('extraHumidity7', None)
        self.extra_hum8 = extra_sensor_config_dict.get('extraHumidity8', None)
        # soil moisture
        self.soil_moist = extra_sensor_config_dict.get('soilMoist', None)
        # soil temp
        self.soil_temp = extra_sensor_config_dict.get('soilTemp', None)
        # leaf wetness
        self.leaf_wet = extra_sensor_config_dict.get('leafWet', None)

        # set trend periods
        self.baro_trend_period = to_int(rtcr_config_dict.get('baro_trend_period',
                                                             DEFAULT_TREND_PERIOD))
        self.temp_trend_period = to_int(rtcr_config_dict.get('temp_trend_period',
                                                             DEFAULT_TREND_PERIOD))
        self.humidity_trend_period = to_int(rtcr_config_dict.get('humidity_trend_period',
                                                             DEFAULT_TREND_PERIOD))
        self.humidex_trend_period = to_int(rtcr_config_dict.get('humidex_trend_period',
                                                             DEFAULT_TREND_PERIOD))

        # ?
        self.new_day = False

        # check to see whether module 'ephem' is installed, without it we can't
        # calculate maxSolarRad
        self.has_ephem = 'ephem' in sys.modules
        # setup max solar rad calcs
        # do we have any?
        calc_dict = config_dict.get('Calculate', {})
        # algorithm
        algo_dict = calc_dict.get('Algorithm', {})
        self.solar_algorithm = algo_dict.get('maxSolarRad', 'RS')
        # atmospheric transmission coefficient [0.7-0.91]
        self.atc = float(calc_dict.get('atc', 0.8))
        # Fail hard if out of range:
        if not 0.7 <= self.atc <= 0.91:
            raise weewx.ViolatedPrecondition("Atmospheric transmission "
                                             "coefficient (%f) out of "
                                             "range [.7-.91]" % self.atc)
        # atmospheric turbidity (2=clear, 4-5=smoggy)
        self.nfac = float(calc_dict.get('nfac', 2))
        # Fail hard if out of range:
        if not 2 <= self.nfac <= 5:
            raise weewx.ViolatedPrecondition("Atmospheric turbidity (%d) "
                                             "out of range (2-5)" % self.nfac)

        if self.min_interval is None:
            _msg = "RealtimeClientraw will generate clientraw.txt. "\
                       "min_interval is None"
        elif self.min_interval == 1:
            _msg = "RealtimeClientraw will generate clientraw.txt. "\
                       "min_interval is 1 second"
        else:
            _msg = "RealtimeClientraw will generate clientraw.txt. min_interval is %s seconds" % self.min_interval
        loginf("engine", _msg)


    def run(self):
        """Collect packets from the rtcr queue and manage their processing.

        Now that we are in a thread get a manager for our db so we can
        initialise our forecast and day stats. Once this is done we wait for
        something in the rtcr queue.
        """

        # would normally do this in our objects __init__ but since we are are
        # running in a thread we need to wait until the thread is actually
        # running before getting db managers

        # get a db manager
        self.db_manager = weewx.manager.open_manager(self.manager_dict)
        # get a db manager for appTemp
        if self.additional_binding:
            self.additional_manager = weewx.manager.open_manager_with_config(self.config_dict,
                                                                             self.additional_binding)
        else:
            self.additional_manager = None
        # initialise our day stats
        self.day_stats = self.db_manager._get_day_summary(time.time())
        # set the unit system for our day stats
        self.day_stats.unit_system = self.db_manager.std_unit_system
        if self.additional_manager:# initialise our day stats from our appTemp source
            self.additional_day_stats = self.additional_manager._get_day_summary(time.time())
            # set the unit system for our day stats
            self.additional_day_stats.unit_system = self.additional_manager.std_unit_system
        else:
            self.additional_day_stats = None
        # create a RtcrBuffer object to hold our loop 'stats'
        self.buffer = RtcrBuffer(day_stats=self.day_stats,
                                 additional_day_stats=self.additional_day_stats)
        # setup our loop cache and set some starting wind values
        _ts = self.db_manager.lastGoodStamp()
        if _ts is not None:
            _rec = self.db_manager.getRecord(_ts)
        else:
            _rec = {'usUnits': None}
        _rec = weewx.units.to_METRICWX(_rec)
        # get a CachedPacket object as our loop packet cache and prime it with
        # values from the last good archive record if available
        logdbg2("rtcrthread", "initialising loop packet cache ...")
        self.packet_cache = CachedPacket(_rec)
        logdbg2("rtcrthread", "loop packet cache initialised")

        # now run a continuous loop, waiting for records to appear in the rtcr
        # queue then processing them.
        while True:
            while True:
                _package = self.rtcr_queue.get()
                # a None record is our signal to exit
                if _package is None:
                    return
                elif _package['type'] == 'archive':
                    self.new_archive_record(_package['payload'])
                    logdbg2("rtcrthread", "received archive record")
                    continue
                elif _package['type'] == 'event':
                    if _package['payload'] == weewx.END_ARCHIVE_PERIOD:
                        logdbg2("rtcrthread",
                                "received event - END_ARCHIVE_PERIOD")
                        self.end_archive_period()
                    continue
                elif _package['type'] == 'stats':
                    logdbg2("rtcrthread",
                            "received stats package payload=%s" % (_package['payload'], ))
                    self.process_stats(_package['payload'])
                    logdbg2("rtcrthread", "processed stats package")
                    continue
                # if packets have backed up in the rtcr queue, trim it until
                # it's no bigger than the max allowed backlog
                if self.rtcr_queue.qsize() <= 5:
                    break

            # we now have a packet to process, wrap in a try..except so we can
            # catch any errors
            try:
                logdbg2("rtcrthread",
                        "received packet: %s" % _package['payload'])
                self.process_packet(_package['payload'])
            except Exception, e:
                # Some unknown exception occurred. This is probably a serious
                # problem. Exit.
                logcrit("rtcrthread",
                        "Unexpected exception of type %s" % (type(e), ))
                weeutil.weeutil.log_traceback('*** ', syslog.LOG_DEBUG)
                logcrit("rtcrthread", "Thread exiting. Reason: %s" % (e, ))
                return

    def process_packet(self, packet):
        """Process incoming loop packets and generate clientraw.txt."""

        # get time for debug timing
        t1 = time.time()

        # we are working MetricWX so convert to MetricWX
        packet_wx = weewx.units.to_METRICWX(packet)

        # update the packet cache with this packet
        self.packet_cache.update(packet_wx, packet_wx['dateTime'])

        # is this the first packet of the day, if so we need to reset our
        # buffer day stats
        dow = time.strftime('%w', time.localtime(packet_wx['dateTime']))
        if self.dow is not None and self.dow != dow:
            self.new_day = True
            self.buffer.start_of_day_reset()
        self.dow = dow

        # if this is the first packet after 9am we need to reset any 9am sums
        # first get the current hour as an int
        _hour = int(time.strftime('%w', time.localtime(packet_wx['dateTime'])))
        # if its a new day and hour>=9 we need to reset any 9am sums
        if self.new_day and _hour >= 9:
            self.new_day = False
            self.buffer.nineam_reset()

        # now add the packet to our buffer
        self.buffer.add_packet(packet_wx)

        # generate if we have no minimum interval setting or if minimum
        # interval seconds have elapsed since our last generation
        if self.min_interval is None or (self.last_write + float(self.min_interval)) < time.time():
            try:
                # get a cached packet
                cached_packet = self.packet_cache.get_packet(packet_wx['dateTime'],
                                                             self.max_cache_age)
                logdbg2("rtcrthread", "cached loop packet: %s" % (cached_packet,))
                # get a data dict from which to construct our file
                data = self.calculate(cached_packet)
                # convert our data dict to a clientraw string
                cr_string = self.create_clientraw_string(data)
                # write our file
                self.write_data(cr_string)
                # set our write time
                self.last_write = time.time()
                # if required send the data to a remote URL via HTTP POST
                if self.remote_server_url is not None:
                    # post the data
                    self.post_data(cr_string)
                # log the generation
                logdbg("rtcrthread",
                       "packet (%s) clientraw.txt generated in %.5f seconds" % (cached_packet['dateTime'],
                                                                                (self.last_write-t1)))
            except Exception, e:
                weeutil.weeutil.log_traceback('rtcrthread: **** ')
        else:
            # we skipped this packet so log it
            logdbg("rtcrthread", "packet (%s) skipped" % packet_wx['dateTime'])

    def process_stats(self, package):
        """Process a stats package.

        Inputs:
            package: dict containing the stats data
        """

        if package is not None:
            for key, value in package.iteritems():
                setattr(self, key, value)

    def new_archive_record(self, record):
        """Control processing when new a archive record is presented.

        When a new archive record is available our interest is in the updated
        daily summaries.
        """

        # refresh our day (archive record based) stats
        self.day_stats = self.db_manager._get_day_summary(record['dateTime'])
        if self.additional_manager:
            self.additional_day_stats = self.additional_manager._get_day_summary(record['dateTime'])

    def end_archive_period(self):
        """Control processing at the end of each archive period."""

        for obs in SUM_MANIFEST:
            self.buffer[obs].interval_reset()

    def post_data(self, data):
        """Post data to a remote URL via HTTP POST.

        This code is modelled on the weeWX restFUL API, but rather then
        retrying a failed post the failure is logged and then ignored. If
        remote posts are not working then the user should set debug=1 and
        restart weeWX to see what the log says.

        The data to be posted is sent as an ascii text string.

        Inputs:
            data: clientraw data string
        """

        # get a Request object
        req = urllib2.Request(self.remote_server_url)
        # set our content type to plain text
        req.add_header('Content-Type', 'text/plain')
        # POST the data but wrap in a try..except so we can trap any errors
        try:
            response = self.post_request(req, data)
            if 200 <= response.code <= 299:
                # No exception thrown and we got a good response code, but did
                # we get self.response back in a return message? Check for
                # self.response, if its there then we can return. If it's
                # not there then log it and return.
                if self.response is not None and self.response not in response:
                    # didn't get 'success' so log it and continue
                    logdbg("post_data",
                           "Failed to post data: Unexpected response")
                return
            # we received a bad response code, log it and continue
            logdbg("post_data",
                   "Failed to post data: Code %s" % response.code())
        except (urllib2.URLError, socket.error,
                httplib.BadStatusLine, httplib.IncompleteRead), e:
            # an exception was thrown, log it and continue
            logdbg("post_data", "Failed to post data: %s" % e)

    def post_request(self, request, payload):
        """Post a Request object.

        Inputs:
            request: urllib2 Request object
            payload: the data to sent

        Returns:
            The urllib2.urlopen() response
        """

        try:
            # Python 2.5 and earlier do not have a "timeout" parameter.
            # Including one could cause a TypeError exception. Be prepared
            # to catch it.
            _response = urllib2.urlopen(request, data=payload, timeout=self.timeout)
        except TypeError:
            # Must be Python 2.5 or early. Use a simple, unadorned request
            _response = urllib2.urlopen(request, data=payload)
        return _response

    def write_data(self, data):
        """Write the clientraw.txt file.

        Takes a string containing the clientraw.txt data and writes it to file.

        Inputs:
            data:   clientraw.txt data string
        """

        with open(self.rtcr_path_file, 'w') as f:
            f.write(data)
            f.write('\n')

    def calculate(self, packet):
        """Calculate the raw clientraw numeric fields.

        Input:
            packet: loop data packet

        Returns:
            Dictionary containg the raw numeric clientraw.txt elements.
        """

        data = dict()
        # preamble
        data[0] = '12345'
        #001 - avg speed (knots)
        if 'windSpeed' in self.buffer:
            avgspeed = self.buffer['windSpeed'].history_avg(packet['dateTime'],
                                                            age=self.avgspeed_period)
            avgspeed_vt = ValueTuple(avgspeed,
                                     'meter_per_second',
                                     'group_speed')
            avgspeed = convert(avgspeed_vt, 'knot').value
        else:
            avgspeed = None
        data[1] = avgspeed if avgspeed is not None else 0.0
        #002 - gust (knots)
        if 'windSpeed' in self.buffer:
            if self.gust_period > 0:
                _gust = self.buffer['windSpeed'].history_max(packet['dateTime'],
                                                            age=self.gust_period).value
            else:
                _gust = self.buffer['windSpeed'].last
            gust_vt = ValueTuple(_gust, 'meter_per_second', 'group_speed')
            gust = convert(gust_vt, 'knot').value
        else:
            gust = None
        data[2] = gust if gust is not None else 0.0
        #003 - windDir
        data[3] = packet['windDir'] if packet['windDir'] is not None else 0.0
        #004 - outTemp (Celsius)
        data[4] = packet['outTemp'] if packet['outTemp'] is not None else 0.0
        #005 - outHumidity
        data[5] = packet['outHumidity'] if packet['outHumidity'] is not None else 0.0
        #006 - barometer(hPa)
        data[6] = packet['barometer'] if packet['barometer'] is not None else 0.0
        #007 - daily rain (mm)
        if 'dayRain' in packet:
            dayRain = packet['dayRain']
        elif 'rain' in self.buffer:
            dayRain = self.buffer['rain'].day_sum
        else:
            dayRain = None
        data[7] = dayRain if dayRain is not None else 0.0
        #008 - monthly rain
        month_rain_vt = getattr(self, 'month_rain_vt',
                                ValueTuple(0, 'mm', 'group_rain'))
        month_rain = convert(month_rain_vt, 'mm').value
        if month_rain and 'rain' in self.buffer:
            month_rain += self.buffer['rain'].interval_sum
        elif 'rain' in self.buffer:
            month_rain = self.buffer['rain'].interval_sum
        else:
            month_rain = None
        data[8] = month_rain if month_rain is not None else 0.0
        #009 - yearly rain
        year_rain_vt = getattr(self, 'year_rain_vt',
                                ValueTuple(0, 'mm', 'group_rain'))
        year_rain = convert(year_rain_vt, 'mm').value
        if year_rain and 'rain' in self.buffer:
            year_rain += self.buffer['rain'].interval_sum
        elif 'rain' in self.buffer:
            year_rain = self.buffer['rain'].interval_sum
        else:
            year_rain = None
        data[9] = year_rain if year_rain is not None else 0.0
        #010 - rain rate (mm per minute - not hour)
        data[10] = packet['rainRate']/60.0 if packet['rainRate'] is not None else 0.0
        #011 - max daily rainRate (mm per minute - not hour)
        if 'rainRate' in self.buffer:
            rainRateTH = self.buffer['rainRate'].day_max
        else:
            rainRateTH = None
        data[11] = rainRateTH/60.0 if rainRateTH is not None else 0.0
        #012 - inTemp (Celsius)
        data[12] = packet['inTemp'] if packet['inTemp'] is not None else 0.0
        #013 - inHumidity
        data[13] = packet['inHumidity'] if packet['inHumidity'] is not None else 0.0
        #014 - soil temperature (Celsius)
        if self.soil_temp and self.soil_temp in packet:
            soil_temp = packet[self.soil_temp]
        else:
            soil_temp = None
        data[14] = soil_temp if soil_temp is not None else 0.0
        #015 - Forecast Icon - ### Fix me
        data[15] = 0
        #016 - WMR968 extra temperature (Celsius) - will not implement
        data[16] = 0.0
        #017 - WMR968 extra humidity (Celsius) - will not implement
        data[17] = 0.0
        #018 - WMR968 extra sensor (Celsius) - will not implement
        data[18] = 0.0
        #019 - yesterday rain (mm)
        yest_rain_vt = getattr(self, 'yest_rain_vt',
                               ValueTuple(0, 'mm', 'group_rain'))
        yest_rain = convert(yest_rain_vt, 'mm').value
        data[19] = yest_rain if yest_rain is not None else 0.0
        #020 - extra temperature sensor 1 (Celsius)
        if self.extra_temp1 and self.extra_temp1 in packet:
            extra_temp1 = packet[self.extra_temp1]
        else:
            extra_temp1 = None
        data[20] = extra_temp1 if extra_temp1 is not None else 0.0
        #021 - extra temperature sensor 2 (Celsius)
        if self.extra_temp2 and self.extra_temp2 in packet:
            extra_temp2 = packet[self.extra_temp2]
        else:
            extra_temp2 = None
        data[21] = extra_temp2 if extra_temp2 is not None else 0.0
        #022 - extra temperature sensor 3 (Celsius)
        if self.extra_temp3 and self.extra_temp3 in packet:
            extra_temp3 = packet[self.extra_temp3]
        else:
            extra_temp3 = None
        data[22] = extra_temp3 if extra_temp3 is not None else 0.0
        #023 - extra temperature sensor 4 (Celsius)
        if self.extra_temp4 and self.extra_temp4 in packet:
            extra_temp4 = packet[self.extra_temp4]
        else:
            extra_temp4 = None
        data[23] = extra_temp4 if extra_temp4 is not None else 0.0
        #024 - extra temperature sensor 5 (Celsius)
        if self.extra_temp5 and self.extra_temp5 in packet:
            extra_temp5 = packet[self.extra_temp5]
        else:
            extra_temp5 = None
        data[24] = extra_temp5 if extra_temp5 is not None else 0.0
        #025 - extra temperature sensor 6 (Celsius)
        if self.extra_temp6 and self.extra_temp6 in packet:
            extra_temp6 = packet[self.extra_temp6]
        else:
            extra_temp6 = None
        data[25] = extra_temp6 if extra_temp6 is not None else 0.0
        #026 - extra humidity sensor 1
        if self.extra_hum1 and self.extra_hum1 in packet:
            extra_hum1 = packet[self.extra_hum1]
        else:
            extra_hum1 = None
        data[26] = extra_hum1 if extra_hum1 is not None else 0.0
        #027 - extra humidity sensor 2
        if self.extra_hum2 and self.extra_hum2 in packet:
            extra_hum2 = packet[self.extra_hum2]
        else:
            extra_hum2 = None
        data[27] = extra_hum2 if extra_hum2 is not None else 0.0
        #028 - extra humidity sensor 3
        if self.extra_hum3 and self.extra_hum3 in packet:
            extra_hum3 = packet[self.extra_hum3]
        else:
            extra_hum3 = None
        data[28] = extra_hum3 if extra_hum3 is not None else 0.0
        #029 - hour
        data[29] = time.strftime('%H', time.localtime(packet['dateTime']))
        #030 - minute
        data[30] = time.strftime('%M', time.localtime(packet['dateTime']))
        #031 - seconds
        data[31] = time.strftime('%S', time.localtime(packet['dateTime']))
        #032 - station name
        hms_string = time.strftime('%H:%M:%S',
                                   time.localtime(packet['dateTime']))
        data[32] = '-'.join([self.location.replace(' ', ''), hms_string])
        #033 - dallas lightning count - will not implement
        data[33] = 0
        #034 - Solar Reading - used as 'solar percent' in Saratoga dashboards
        percent = None
        if 'radiation' in packet and packet['radiation'] is not None:
            if 'maxSolarRad' in packet and packet['maxSolarRad'] is not None:
                percent = 100.0 * packet['radiation']/packet['maxSolarRad']
            elif self.has_ephem:
                # pyephem is installed so we can calculate maxSolarRad, how we
                # do it depends
                if self.solar_algorithm == 'Bras':
                    curr_solar_max = weewx.wxformulas.solar_rad_Bras(self.latitude,
                                                                     self.longitude,
                                                                     self.altitude_m,
                                                                     packet['dateTime'],
                                                                     self.nfac)
                else:
                    curr_solar_max = weewx.wxformulas.solar_rad_RS(self.latitude,
                                                                   self.longitude,
                                                                   self.altitude_m,
                                                                   packet['dateTime'],
                                                                   self.atc)
                if curr_solar_max is not None:
                    percent = 100.0 * packet['radiation']/curr_solar_max
                else:
                    curr_solar_max = None
        data[34] = percent if percent is not None else 0.0
        #035 - Day
        data[35] = time.strftime('%-d', time.localtime(packet['dateTime']))
        #036 - Month
        data[36] = time.strftime('%-m', time.localtime(packet['dateTime']))
        #037 - WMR968/200 battery 1 - will not implement
        data[37] = 100
        #038 - WMR968/200 battery 2 - will not implement
        data[38] = 100
        #039 - WMR968/200 battery 3 - will not implement
        data[39] = 100
        #040 - WMR968/200 battery 4 - will not implement
        data[40] = 100
        #041 - WMR968/200 battery 5 - will not implement
        data[41] = 100
        #042 - WMR968/200 battery 6 - will not implement
        data[42] = 100
        #043 - WMR968/200 battery 7 - will not implement
        data[43] = 100
        #044 - windchill (Celsius)
        data[44] = packet['windchill'] if packet['windchill'] is not None else 0.0
        #045 - humidex (Celsius)
        if 'humidex' in packet:
            humidex = packet['humidex']
        elif 'outTemp' in packet and 'outHumididty' in packet:
            humidex = weewx.wxformulas.humidexC(packet['outTemp'],
                                                packet['outHumidity'])
        data[45] = humidex if humidex is not None else 0.0
        #046 - maximum day temperature (Celsius)
        if 'outTemp' in self.buffer:
            tempTH = self.buffer['outTemp'].day_max
        else:
            tempTH = None
        data[46] = tempTH if tempTH is not None else 0.0
        #047 - minimum day temperature (Celsius)
        if 'outTemp' in self.buffer:
            tempTL = self.buffer['outTemp'].day_min
        else:
            tempTL = None
        data[47] = tempTL if tempTL is not None else 0.0
        #048 - icon type - ### Fix me)
        data[48] = 0
        #049 - weather description - ### Fix me
        data[49] = '---'
        #050 - barometer trend (hPa)
        baro_vt = ValueTuple(packet['barometer'], 'hPa', 'group_pressure')
        baro_trend = calc_trend('barometer', baro_vt, self.db_manager,
                                packet['dateTime'] - self.baro_trend_period,
                                self.grace)
        data[50] = baro_trend if baro_trend is not None else 0.0
        #051-070 incl - windspeed hour 01-20 incl (knots) - will not implement
        for h in range(0,20):
            data[51+h] = 0.0
        #071 - maximum wind gust today
        if 'windSpeed' in self.buffer:
            windGustTM = self.buffer['windSpeed'].day_max
        else:
            windGustTM = 0.0
        # our speeds are in m/s need to convert to knots
        windGustTM_vt = ValueTuple(windGustTM, 'meter_per_second', 'group_speed')
        windGustTM = convert(windGustTM_vt, 'knot').value
        data[71] = windGustTM if windGustTM is not None else 0.0
        #072 - dewpoint (Celsius)
        data[72] = packet['dewpoint'] if packet['dewpoint'] is not None else 0.0
        #073 - cloud height (foot)
        if 'cloudbase' in packet:
            cb = packet['cloudbase']
        else:
            if 'outTemp' in packet and 'outHumidity' in packet:
                cb = weewx.wxformulas.cloudbase_Metric(packet['outTemp'],
                                                       packet['outHumidity'],
                                                       self.altitude_m)
            else:
                cb = None
        # our altitudes are in metres, need to convert to feet
        cloudbase_vt = ValueTuple(cb, 'meter', 'group_altitude')
        cloudbase = convert(cloudbase_vt, 'foot').value
        data[73] = cloudbase if cloudbase is not None else 0.0
        #074 -  date
        data[74] = time.strftime('%-d/%-m/%Y', time.localtime(packet['dateTime']))
        #075 - maximum day humidex (Celsius)
        #076 - minimum day numidex (Celsius)
        if 'humidex' in self.buffer:
            humidexTH = self.buffer['humidex'].day_max
            humidexTL = self.buffer['humidex'].day_min
        else:
            humidexTH = None
            humidexTL = None
        data[75] = humidexTH if humidexTH is not None else 0.0
        data[76] = humidexTL if humidexTL is not None else 0.0
        #077 - maximum day windchill (Celsius)
        #078 - minimum day windchill (Celsius)
        if 'windchill' in self.buffer:
            windchillTH = self.buffer['windchill'].day_max
            windchillTL = self.buffer['windchill'].day_min
        else:
            windchillTH = None
            windchillTL = None
        data[77] = windchillTH if windchillTH is not None else 0.0
        data[78] = windchillTL if windchillTL is not None else 0.0
        #079 - davis vp UV
        data[79] = packet['UV'] if packet['UV'] is not None else 0
        #080-089 - hour windspeed 01-10 - will not implement
        for h in range(0,10):
            data[80+h] = 0.0
        #090-099 - hour temperature 01-10 (Celsius) - will not implement
        for h in range(0,10):
            data[90+h] = 0.0
        #100-109 - hour rain 01-10 (mm) - will not implement
        for h in range(0,10):
            data[100+h] = 0.0
        #110 - maximum day heatindex (Celsius)
        #111 - minimum day heatindex (Celsius)
        if 'heatindex' in self.buffer:
            heatindexTH = self.buffer['heatindex'].day_max
            heatindexTL = self.buffer['heatindex'].day_min
        else:
            heatindexTH = None
            heatindexTL = None
        data[110] = heatindexTH if heatindexTH is not None else 0.0
        data[111] = heatindexTL if heatindexTL is not None else 0.0
        #112 - heatindex (Celsius)
        data[112] = packet['heatindex'] if packet['heatindex'] is not None else 0.0
        #113 - maximum average speed (knot) - ### fix me - how to calculate
        if 'windSpeed' in self.buffer:
            windSpeedTM_loop = self.buffer['windSpeed'].day_max
        else:
            windSpeedTM_loop = 0.0
        if 'windSpeed' in self.day_stats:
            windSpeedTM = self.day_stats['windSpeed'].max
        else:
            windSpeedTM = 0.0
        windSpeedTM = weeutil.weeutil.max_with_none([windSpeedTM, windSpeedTM_loop])
        windSpeedTM_vt = ValueTuple(windSpeedTM, 'km_per_hour', 'group_speed')
        windSpeedTM = convert(windSpeedTM_vt, 'knot').value
        data[113] = windSpeedTM if windSpeedTM is not None else 0.0
        #114 - lightning count in last minute - will not implement
        data[114] = 0
        #115 - time of last lightning strike - will not implement
        data[115] = '00:00'
        #116 - date of last lightning strike - will not implement
        data[116] = '---'
        #117 - wind average direction
        data[117] = self.buffer['wind'].vec_dir
        #118 - nexstorm distance - will not implement
        data[118] = 0.0
        #119 - nexstorm bearing - will not implement
        data[119] = 0.0
        #120 - extra temperature sensor 7 (Celsius)
        if self.extra_temp7 and self.extra_temp7 in packet:
            extra_temp7 = packet[self.extra_temp7]
        else:
            extra_temp7 = None
        data[120] = extra_temp7 if extra_temp7 is not None else 0.0
        #121 - extra temperature sensor 8 (Celsius)
        if self.extra_temp8 and self.extra_temp8 in packet:
            extra_temp8 = packet[self.extra_temp8]
        else:
            extra_temp8 = None
        data[121] = extra_temp8 if extra_temp8 is not None else 0.0
        #122 - extra humidity sensor 4
        if self.extra_hum4 and self.extra_hum4 in packet:
            extra_hum4 = packet[self.extra_hum4]
        else:
            extra_hum4 = None
        data[122] = extra_hum4 if extra_hum4 is not None else 0.0
        #123 - extra humidity sensor 5
        if self.extra_hum5 and self.extra_hum5 in packet:
            extra_hum5 = packet[self.extra_hum5]
        else:
            extra_hum5 = None
        data[123] = extra_hum5 if extra_hum5 is not None else 0.0
        #124 - extra humidity sensor 6
        if self.extra_hum6 and self.extra_hum6 in packet:
            extra_hum6 = packet[self.extra_hum6]
        else:
            extra_hum6 = None
        data[124] = extra_hum6 if extra_hum6 is not None else 0.0
        #125 - extra humidity sensor 7
        if self.extra_hum7 and self.extra_hum7 in packet:
            extra_hum7 = packet[self.extra_hum7]
        else:
            extra_hum7 = None
        data[125] = extra_hum7 if extra_hum7 is not None else 0.0
        #126 - extra humidity sensor 8
        if self.extra_hum8 and self.extra_hum8 in packet:
            extra_hum8 = packet[self.extra_hum8]
        else:
            extra_hum8 = None
        data[126] = extra_hum8 if extra_hum8 is not None else 0.0
        #127 - vp solar
        data[127] = packet['radiation'] if packet['radiation'] is not None else 0.0
        #128 - maximum inTemp (Celsius)
        #129 - minimum inTemp (Celsius)
        if 'inTemp' in self.buffer:
            inTempTH = self.buffer['inTemp'].day_max
            inTempTL = self.buffer['inTemp'].day_min
        else:
            inTempTH = None
            inTempTL = None
        data[128] = inTempTH if inTempTH is not None else 0.0
        data[129] = inTempTL if inTempTL is not None else 0.0
        #130 - appTemp (Celsius)
        if 'appTemp' in packet:
            appTemp = packet['appTemp']
        elif 'windSpeed' in packet and 'outTemp' in parcket and 'outHumidity' in packet:
            windSpeed_vt = ValueTuple(packet['windSpeed'], 'km_per_hour', 'group_speed')
            windSpeed_MS = convert(windSpeed_vt, 'meter_per_second').value
            appTemp = weewx.wxformulas.apptempC(packet['outTemp'],
                                                packet['outHumidity'],
                                                windspeed_MS)
        else:
            appTemp = None
        data[130] = appTemp if appTemp is not None else 0.0
        #131 - maximum barometer (hPa)
        #132 - minimum barometer (hPa)
        if 'barometer' in self.buffer:
            barometerTH = self.buffer['barometer'].day_max
            barometerTL = self.buffer['barometer'].day_min
        else:
            barometerTH = None
            barometerTL = None
        data[131] = barometerTH if barometerTH is not None else 0.0
        data[132] = barometerTL if barometerTL is not None else 0.0
        #133 - maximum windGust last hour (knot) - ### fix me - how to calculate
        hour_gust_vt = getattr(self, 'hour_gust_vt',
                               ValueTuple(0, 'knot', 'group_speed'))
        if hour_gust_vt.value and 'windSpeed' in self.buffer:
            windSpeedTM_loop = self.buffer['windSpeed'].day_max
        else:
            windSpeedTM_loop = None
        windGust60 = weeutil.weeutil.max_with_none([hour_gust_vt.value,
                                                   windSpeedTM_loop])
        windGust60_vt = ValueTuple(windGust60, 'meter_per_second', 'group_speed')
        windGust60 = convert(windGust60_vt, 'knot').value
        data[133] = windGust60 if windGust60 is not None else 0.0
        #134 - maximum windGust in last hour time - ### Fix me - how to calculate
        data[134] = time.strftime('%H:%M', time.localtime(packet['dateTime']))
        #135 - maximum windGust today time
        if 'windSpeed' in self.buffer:
            TwindGustTM_ts = self.buffer['windSpeed'].day_maxtime
            if TwindGustTM_ts is not None:
                TwindGustTM = time.localtime(TwindGustTM_ts)
            else:
                TwindGustTM = time.localtime(packet['dateTime'])
        else:
            TwindGustTM = time.localtime(packet['dateTime'])
        data[135] = time.strftime('%H:%M', TwindGustTM)
        #136 - maximum day appTemp (Celsius)
        #137 - minimum day appTemp (Celsius)
        if 'appTemp' in self.buffer:
            appTempTH = self.buffer['appTemp'].day_max
            appTempTL = self.buffer['appTemp'].day_min
        else:
            appTempTH = None
            appTempTL = None
        data[136] = appTempTH if appTempTH is not None else 0.0
        data[137] = appTempTL if appTempTL is not None else 0.0
        # 138 - maximum day dewpoint (Celsius)
        # 139 - minimum day dewpoint (Celsius)
        if 'dewpoint' in self.buffer:
            dewpointTH = self.buffer['dewpoint'].day_max
            dewpointTL = self.buffer['dewpoint'].day_min
        else:
            dewpointTH = None
            dewpointTL = None
        data[138] = dewpointTH if dewpointTH is not None else 0.0
        data[139] = dewpointTL if dewpointTL is not None else 0.0
        #140 - maximum windGust in last minute (knot)
        if 'windSpeed' in self.buffer:
            _gust1_ot = self.buffer['windSpeed'].history_max(packet['dateTime'],
                                                        age=60)
            gust1_vt = ValueTuple(_gust1_ot.value,
                                  'meter_per_second',
                                  'group_speed')
            gust1 = convert(gust1_vt, 'knot').value
        else:
            gust1 = None
        data[140] = gust1 if gust1 is not None else 0.0
        #141 - current year
        data[141] = time.strftime('%Y', time.localtime(packet['dateTime']))
        #142 - THSWS - will not implement
        data[142] = 0.0
        #143 - outTemp trend (logic)
        temp_vt = ValueTuple(packet['outTemp'], 'degree_C', 'group_temperature')
        temp_trend = calc_trend('outTemp', temp_vt, self.db_manager,
                                packet['dateTime'] - self.temp_trend_period,
                                self.grace)
        if temp_trend is None or temp_trend == 0:
            _trend = '0'
        elif temp_trend > 0:
            _trend = '+1'
        else:
            _trend = '-1'
        data[143] = _trend
        #144 - outHumidity trend (logic)
        hum_vt = ValueTuple(packet['outHumidity'], 'percent', 'group_percent')
        hum_trend = calc_trend('outHumidity', hum_vt, self.db_manager,
                               packet['dateTime'] - self.humidity_trend_period,
                               self.grace)
        if hum_trend is None or hum_trend == 0:
            _trend = '0'
        elif hum_trend > 0:
            _trend = '+1'
        else:
            _trend = '-1'
        data[144] = _trend
        #145 - humidex trend (logic)
        humidex_vt = ValueTuple(packet['humidex'], 'degree_C', 'group_temperature')
        humidex_trend = calc_trend('humidex', humidex_vt, self.db_manager,
                                   packet['dateTime'] - self.humidex_trend_period,
                                   self.grace)
        if humidex_trend is None or humidex_trend == 0:
            _trend = '0'
        elif humidex_trend > 0:
            _trend = '+1'
        else:
            _trend = '-1'
        data[145] = _trend
        #146-155 - hour wind direction 01-10 - will not implement
        for h in range(0,10):
            data[146+h] = 0.0
        #156 - leaf wetness
        if self.leaf_wet and self.leaf_wet in packet:
            leaf_wet = packet[self.leaf_wet]
        else:
            leaf_wet = None
        data[156] = leaf_wet if leaf_wet is not None else 0.0
        #157 - soil moisture
        if self.soil_moist and self.soil_moist in packet:
            soil_moist = packet[self.soil_moist]
        else:
            soil_moist = None
        data[157] = soil_moist if soil_moist is not None else 255.0
        #158 - 10 minute average wind speed (knot)
        if 'windSpeed' in self.buffer:
            avgspeed10 = self.buffer['windSpeed'].history_avg(packet['dateTime'],
                                                            age=600)
            avgspeed10_vt = ValueTuple(avgspeed10,
                                       'meter_per_second',
                                       'group_speed')
            avgspeed10 = convert(avgspeed10_vt, 'knot').value
        else:
            avgspeed10 = None
        data[158] = avgspeed10 if avgspeed10 is not None else 0.0
        #159 - wet bulb temperature (Celsius)
        WB = calc_wetbulb(packet['outTemp'],
                          packet['outHumidity'],
                          packet['barometer'])
        data[159] = WB if WB is not None else 0.0
        #160 - latitude (-ve for south)
        data[160] = self.latitude
        #161 -  longitude (-ve for east)
        data[161] = -1 * self.longitude
        #162 - 9am reset rainfall total (mm)
        data[162] = self.buffer['rain'].nineam_sum
        #163 - high day outHumidity
        #164 - low day outHumidity
        if 'outHumidity' in self.buffer:
            outHumidityTH = self.buffer['outHumidity'].day_max
            outHumidityTL = self.buffer['outHumidity'].day_min
        else:
            outHumidityTH = None
            outHumidityTL = None
        data[163] = outHumidityTH if outHumidityTH is not None else 0.0
        data[164] = outHumidityTL if outHumidityTL is not None else 0.0
        #165 - midnight rain reset total (mm)
        if 'dayRain' in packet:
            dayRain = packet['dayRain']
        elif 'rain' in self.buffer:
            dayRain = self.buffer['rain'].day_sum
        else:
            dayRain = None
        data[165] = dayRain if dayRain is not None else 0.0
        #166 - low day windchill time
        if 'windchill' in self.buffer:
            TwchillTM_ts = self.buffer['windchill'].day_mintime
            if TwchillTM_ts is not None:
                TwchillTM = time.localtime(TwchillTM_ts)
            else:
                TwchillTM = time.localtime(packet['dateTime'])
        else:
            TwchillTM = time.localtime(packet['dateTime'])
        data[166] = time.strftime('%H:%M', TwchillTM)
        #167 - Current Cost Channel 1 - will not implement
        data[167] = 0.0
        #168 - Current Cost Channel 2 - will not implement
        data[168] = 0.0
        #169 - Current Cost Channel 3 - will not implement
        data[169] = 0.0
        #170 - Current Cost Channel 4 - will not implement
        data[170] = 0.0
        #171 - Current Cost Channel 5 - will not implement
        data[171] = 0.0
        #172 - Current Cost Channel 6 - will not implement
        data[172] = 0.0
        #173 - day windrun
        data[173] = self.buffer.windrun if self.buffer.windrun is not None else 0.0
        #174 - record end (WD Version)
        data[174] = '!!EOR!!'
        return data

    def create_clientraw_string(self, data):
        """Create the clientraw string from the clientraw data.

        The raw clientraw data is a dict of numbers and strings. This method
        formats each field appropriately and generates the string that
        comprises the clienraw.txt fiel contents.

        Input:
            data: a dict containing the raw clientraw data

        Returns:
            A string containing the formatted clientraw.txt contents.
        """

        fields = []
        fields.append(data[0])
        fields.append(self.format(data[1], 1))
        fields.append(self.format(data[2], 1))
        fields.append(self.format(data[3], 0))
        fields.append(self.format(data[4], 1))
        fields.append(self.format(data[5], 1))
        fields.append(self.format(data[6], 1))
        fields.append(self.format(data[7], 1))
        fields.append(self.format(data[8], 1))
        fields.append(self.format(data[9], 1))
        fields.append(self.format(data[10], 1))
        fields.append(self.format(data[11], 1))
        fields.append(self.format(data[12], 1))
        fields.append(self.format(data[13], 1))
        fields.append(self.format(data[14], 1))
        fields.append(self.format(data[15], 0))
        fields.append(self.format(data[16], 1))
        fields.append(self.format(data[17], 1))
        fields.append(self.format(data[18], 1))
        fields.append(self.format(data[19], 1))
        fields.append(self.format(data[20], 1))
        fields.append(self.format(data[21], 1))
        fields.append(self.format(data[22], 1))
        fields.append(self.format(data[23], 1))
        fields.append(self.format(data[24], 1))
        fields.append(self.format(data[25], 1))
        fields.append(self.format(data[26], 1))
        fields.append(self.format(data[27], 1))
        fields.append(self.format(data[28], 1))
        fields.append(data[29])
        fields.append(data[30])
        fields.append(data[31])
        fields.append(data[32])
        fields.append(self.format(data[33], 0))
        fields.append(self.format(data[34], 0))
        fields.append(data[35])
        fields.append(data[36])
        fields.append(self.format(data[37], 0))
        fields.append(self.format(data[38], 0))
        fields.append(self.format(data[39], 0))
        fields.append(self.format(data[40], 0))
        fields.append(self.format(data[41], 0))
        fields.append(self.format(data[42], 0))
        fields.append(self.format(data[43], 0))
        fields.append(self.format(data[44], 1))
        fields.append(self.format(data[45], 1))
        fields.append(self.format(data[46], 1))
        fields.append(self.format(data[47], 1))
        fields.append(self.format(data[48], 0))
        fields.append(data[49])
        fields.append(self.format(data[50], 1))
        fields.append(self.format(data[51], 1))
        fields.append(self.format(data[52], 1))
        fields.append(self.format(data[53], 1))
        fields.append(self.format(data[54], 1))
        fields.append(self.format(data[55], 1))
        fields.append(self.format(data[56], 1))
        fields.append(self.format(data[57], 1))
        fields.append(self.format(data[58], 1))
        fields.append(self.format(data[59], 1))
        fields.append(self.format(data[60], 1))
        fields.append(self.format(data[61], 1))
        fields.append(self.format(data[62], 1))
        fields.append(self.format(data[63], 1))
        fields.append(self.format(data[64], 1))
        fields.append(self.format(data[65], 1))
        fields.append(self.format(data[66], 1))
        fields.append(self.format(data[67], 1))
        fields.append(self.format(data[68], 1))
        fields.append(self.format(data[69], 1))
        fields.append(self.format(data[70], 1))
        fields.append(self.format(data[71], 1))
        fields.append(self.format(data[72], 1))
        fields.append(self.format(data[73], 1))
        fields.append(data[74])
        fields.append(self.format(data[75], 1))
        fields.append(self.format(data[76], 1))
        fields.append(self.format(data[77], 1))
        fields.append(self.format(data[78], 1))
        fields.append(self.format(data[79], 1))
        fields.append(self.format(data[80], 1))
        fields.append(self.format(data[81], 1))
        fields.append(self.format(data[81], 1))
        fields.append(self.format(data[81], 1))
        fields.append(self.format(data[81], 1))
        fields.append(self.format(data[81], 1))
        fields.append(self.format(data[81], 1))
        fields.append(self.format(data[81], 1))
        fields.append(self.format(data[81], 1))
        fields.append(self.format(data[81], 1))
        fields.append(self.format(data[91], 1))
        fields.append(self.format(data[91], 1))
        fields.append(self.format(data[91], 1))
        fields.append(self.format(data[91], 1))
        fields.append(self.format(data[91], 1))
        fields.append(self.format(data[91], 1))
        fields.append(self.format(data[91], 1))
        fields.append(self.format(data[91], 1))
        fields.append(self.format(data[91], 1))
        fields.append(self.format(data[91], 1))
        fields.append(self.format(data[100], 1))
        fields.append(self.format(data[101], 1))
        fields.append(self.format(data[102], 1))
        fields.append(self.format(data[103], 1))
        fields.append(self.format(data[104], 1))
        fields.append(self.format(data[105], 1))
        fields.append(self.format(data[106], 1))
        fields.append(self.format(data[107], 1))
        fields.append(self.format(data[108], 1))
        fields.append(self.format(data[109], 1))
        fields.append(self.format(data[110], 1))
        fields.append(self.format(data[111], 1))
        fields.append(self.format(data[112], 1))
        fields.append(self.format(data[113], 1))
        fields.append(self.format(data[114], 0))
        fields.append(data[115])
        fields.append(data[116])
        fields.append(self.format(data[117], 1))
        fields.append(self.format(data[118], 1))
        fields.append(self.format(data[119], 1))
        fields.append(self.format(data[120], 1))
        fields.append(self.format(data[121], 1))
        fields.append(self.format(data[122], 0))
        fields.append(self.format(data[123], 0))
        fields.append(self.format(data[124], 0))
        fields.append(self.format(data[125], 0))
        fields.append(self.format(data[126], 0))
        fields.append(self.format(data[127], 1))
        fields.append(self.format(data[128], 1))
        fields.append(self.format(data[129], 1))
        fields.append(self.format(data[130], 1))
        fields.append(self.format(data[131], 1))
        fields.append(self.format(data[132], 1))
        fields.append(self.format(data[133], 1))
        fields.append(data[134])
        fields.append(data[135])
        fields.append(self.format(data[136], 1))
        fields.append(self.format(data[137], 1))
        fields.append(self.format(data[138], 1))
        fields.append(self.format(data[139], 1))
        fields.append(self.format(data[140], 1))
        fields.append(data[141])
        fields.append(self.format(data[142], 1))
        fields.append(self.format(data[143], 1))# Fix me
        fields.append(self.format(data[144], 1))# Fix me
        fields.append(self.format(data[145], 1))# Fix me
        fields.append(self.format(data[146], 1))
        fields.append(self.format(data[147], 1))
        fields.append(self.format(data[148], 1))
        fields.append(self.format(data[149], 1))
        fields.append(self.format(data[150], 1))
        fields.append(self.format(data[151], 1))
        fields.append(self.format(data[152], 1))
        fields.append(self.format(data[153], 1))
        fields.append(self.format(data[154], 1))
        fields.append(self.format(data[155], 1))
        fields.append(self.format(data[156], 1))
        fields.append(self.format(data[157], 1))
        fields.append(self.format(data[158], 1))
        fields.append(self.format(data[159], 1))
        fields.append(self.format(data[160], 1))# Fix me
        fields.append(self.format(data[161], 1))# Fix me
        fields.append(self.format(data[162], 1))
        fields.append(self.format(data[163], 1))
        fields.append(self.format(data[164], 1))
        fields.append(self.format(data[165], 1))
        fields.append(data[166])
        fields.append(self.format(data[167], 1))
        fields.append(self.format(data[168], 1))
        fields.append(self.format(data[169], 1))
        fields.append(self.format(data[170], 1))
        fields.append(self.format(data[171], 1))
        fields.append(self.format(data[172], 1))
        fields.append(self.format(data[173], 1))
        fields.append(data[174])
        return ' '.join(fields)

    def format(self, data, places=None):
        """Format a number as a string with a given number of decimal places.

        Inputs:
            data:   The data to be formatted. May be a number or string
                    representation of a number.
            places: The number of decimal places to which the data will be
                    rounded.

        Returns:
            A string containing the data rounded and formatted to places
            decimal places. If data is None '0.0' is returned. If places is
            None or omitted the data is returned as received but converted to a
            string.
        """

        result = data
        if data is None:
            result = '0.0'
        elif places is not None:
            try:
                _v = float(data)
                _format = "%%.%df" % places
                result = _format % _v
            except ValueError:
                pass
        return str(result)


# ============================================================================
#                             class VectorBuffer
# ============================================================================


class VectorBuffer(object):
    """Class to buffer vector obs."""

    default_init = (None, None, None, None)

    def __init__(self, stats, history=False, sum=False):
        self.last     = None
        self.lasttime = None
        if stats:
            self.day_min = stats.min
            self.day_mintime = stats.mintime
            self.day_max = stats.max
            self.day_maxtime = stats.maxtime
        else:
            (self.day_min, self.day_mintime,
             self.day_max, self.day_maxtime) = VectorBuffer.default_init
        if history:
            self.history = []
            self.history_full = False
        if sum:
            if stats:
                self.day_sum = stats.sum
                self.day_xsum = stats.xsum
                self.day_ysum = stats.ysum
            else:
                self.day_sum = 0.0
                self.day_xsum = 0.0
                self.day_ysum = 0.0
            self.nineam_sum = 0.0
            self.interval_sum = 0.0

    def _add_value(self, val, ts, hilo, history, sum):
        """Add a value to my hilo and history stats as required."""

        (w_speed, w_dir) = val
        if w_speed is not None:
            if self.lasttime is None or ts >= self.lasttime:
                self.last    = (w_speed, w_dir)
                self.lasttime= ts
            if hilo:
                if self.day_min is None or w_speed < self.day_min:
                    self.day_min     = w_speed
                    self.day_mintime = ts
                if self.day_max is None or w_speed > self.day_max:
                    self.day_max     = w_speed
                    self.day_maxtime = ts
            if history:
                self.history.append(ObsTuple((w_speed,
                                              math.cos(math.radians(90.0 - w_dir)),
                                              math.sin(math.radians(90.0 - w_dir))), ts))
#                self.history.append(ObsTuple((round(w_speed,4),
#                                              round(math.cos(math.radians(90.0 - w_dir)),4),
#                                              round(math.sin(math.radians(90.0 - w_dir)),4)), ts))
#                loginf("","speed=%s dir=%s" % (w_speed, w_dir))
#                loginf("","self.history=%s" % (self.history,))
                self.trim_history(ts)
            if sum:
                self.day_sum += w_speed
                if w_dir is not None:
                    self.day_xsum = w_speed * math.cos(math.radians(90.0 - w_dir))
                    self.day_ysum = w_speed * math.sin(math.radians(90.0 - w_dir))

    def day_reset(self):
        """Reset the vector obs buffer."""

        (self.day_min, self.day_mintime,
         self.day_max, self.day_maxtime) = VectorBuffer.default_init
        try:
            self.day_sum = 0.0
        except AttributeError:
            pass

    def nineam_reset(self):
        """Reset the vector obs buffer."""

        self.nineam_sum = 0.0

    def interval_reset(self):
        """Reset the vector obs buffer."""

        self.interval_sum = 0.0

    def trim_history(self, ts):
        """Trim an old data from the history list."""

        # calc ts of oldest sample we want to retain
        oldest_ts = ts - MAX_AGE
        # set history_full
        self.history_full = min([a.ts for a in self.history if a.ts is not None]) <= oldest_ts
        # remove any values older than oldest_ts
        self.history = [s for s in self.history if s.ts > oldest_ts]

    def history_max(self, ts, age=MAX_AGE):
        """Return the max value in my history.

        Search the last age seconds of my history for the max value and the
        corresponding timestamp.

        Inputs:
            ts:  the timestamp to start searching back from
            age: the max age of the records being searched

        Returns:
            An object of type ObsTuple where value is a 3 way tuple of (value, x component, y comentent) and
            ts is the timestamp when it ocurred.
        """

        born = ts - age
        snapshot = [a for a in self.history if a.ts >= born]
        if len(snapshot) > 0:
            _max = max(snapshot,key=itemgetter(1)[0])
            return ObsTuple(_max[0], _max[1])
        else:
            return None

    def history_avg(self, ts, age=MAX_AGE):
        """Return the average value in my history.

        Search the last age seconds of my history for the max value and the
        corresponding timestamp.

        Inputs:
            ts:  the timestamp to start searching back from
            age: the max age of the records being searched

        Returns:
            An object of type ObsTuple where value is a 3 way tuple of (value, x component, y comentent) and
            ts is the timestamp when it ocurred.
        """

        born = ts - age
        snapshot = [a.value[0] for a in self.history if a.ts >= born]
        if len(snapshot) > 0:
            return sum(snapshot)/len(snapshot)
        else:
            return None

    def history_vec_avg(self, ts, age=MAX_AGE):
        """Return the my history vector average."""

        born = ts - age
        rec = [a.value for a in self.history if a.ts >= born]
        if len(rec) > 0:
            x = 0
            y = 0
            for sample in rec:
                x += sample[0] * sample[1] if sample[1] is not None else 0.0
                y += sample[0] * sample[2] if sample[2] is not None else 0.0
            _dir = 90.0 - math.degrees(math.atan2(y, x))
            if _dir < 0.0:
                _dir += 360.0
            _value = math.sqrt(pow(x, 2) + pow(y, 2))
            return (_value, _dir)
        else:
            return None

    @property
    def vec_dir(self):
        """The day vector average direction."""

        _result = 90.0 - math.degrees(math.atan2(self.day_ysum, self.day_xsum))
        if _result < 0.0:
            _result += 360.0
        return _result


# ============================================================================
#                             class ScalarBuffer
# ============================================================================


class ScalarBuffer(object):
    """Class to buffer scalar obs."""

    default_init = (None, None, None, None)

    def __init__(self, stats, history=False, sum=False):
        self.last     = None
        self.lasttime = None
        if stats:
            self.day_min = stats.min
            self.day_mintime = stats.mintime
            self.day_max = stats.max
            self.day_maxtime = stats.maxtime
        else:
            (self.day_min, self.day_mintime,
             self.day_max, self.day_maxtime) = ScalarBuffer.default_init
        if history:
            self.history = []
            self.history_full = False
        if sum:
            if stats:
                self.day_sum = stats.sum
            else:
                self.day_sum = 0.0
            self.nineam_sum = 0.0
            self.interval_sum = 0.0


    def _add_value(self, val, ts, hilo, history, sum):
        """Add a value to my hilo and history stats as required."""

        if val is not None:
            if self.lasttime is None or ts >= self.lasttime:
                self.last    = val
                self.lasttime= ts
            if hilo:
                if self.day_min is None or val < self.day_min:
                    self.day_min     = val
                    self.day_mintime = ts
                if self.day_max is None or val > self.day_max:
                    self.day_max     = val
                    self.day_maxtime = ts
            if history:
                self.history.append(ObsTuple(val, ts))
                self.trim_history(ts)
            if sum:
                self.day_sum += val
                self.nineam_sum += val
                self.interval_sum += val

    def day_reset(self):
        """Reset the scalar obs buffer."""

        (self.day_min, self.day_mintime,
         self.day_max, self.day_maxtime) = ScalarBuffer.default_init
        try:
            self.day_sum = 0.0
        except AttributeError:
            pass

    def nineam_reset(self):
        """Reset the scalar obs buffer."""

        self.nineam_sum = 0.0

    def interval_reset(self):
        """Reset the scalar obs buffer."""

        self.interval_sum = 0.0

    def trim_history(self, ts):
        """Trim an old data from the history list."""

        # calc ts of oldest sample we want to retain
        oldest_ts = ts - MAX_AGE
        # set history_full
        self.history_full = min([a.ts for a in self.history if a.ts is not None]) <= oldest_ts
        # remove any values older than oldest_ts
        self.history = [s for s in self.history if s.ts > oldest_ts]

    def history_max(self, ts, age=MAX_AGE):
        """Return the max value in my history.

        Search the last age seconds of my history for the max value and the
        corresponding timestamp.

        Inputs:
            ts:  the timestamp to start searching back from
            age: the max age of the records being searched

        Returns:
            An object of type ObsTuple where value is the max value found and
            ts is the timestamp when it ocurred.
        """

        born = ts - age
        snapshot = [a for a in self.history if a.ts >= born]
        if len(snapshot) > 0:
            _max = max(snapshot,key=itemgetter(1))
            return ObsTuple(_max[0], _max[1])
        else:
            return None

    def history_avg(self, ts, age=MAX_AGE):
        """Return my average."""

        if len(self.history) > 0:
            born = ts - age
            rec = [a.value for a in self.history if a.ts >= born]
            return float(sum(rec))/len(rec)
        else:
            return None


# ============================================================================
#                             class RtcrBuffer
# ============================================================================


class RtcrBuffer(dict):
    """Class to buffer various loop packet obs.

    Archive based stats are an efficient means of obtaining stats for today.
    However, their use ignores any max/min etc (eg todays max outTemp) that
    'occurs' after the most recent archive record but before the next archive
    record is written to archive. For this reason selected loop data is
    buffered to enable 'loop' stats to be calculated. Accurate daily stats can
    then be determined at any time using a combination of archive based and
    loop based stats.

    The loop based stats are maintained over the period since the last archive
    record was generated. The loop based stats are reset each time an archive
    record is generated.

    Selected observations also have a history of loop value, timestamp pairs
    maintained to enable calculation of short term ma/min stats eg 'max
    windSpeed in last minute'. These histories are based on a moving window of
    a given period eg 10 minutes and are updated each time a looppacket is
    received.
    """

    def __init__(self, day_stats, additional_day_stats=None, unit_system=weewx.METRICWX):
        """Initialise an instance of our class."""

        # seed our buffer objects from day_stats
        for obs in [f for f in day_stats if f in MANIFEST]:
            seed_func = seed_functions.get(obs, RtcrBuffer.seed_scalar)
            seed_func(self, day_stats[obs], obs,
                      obs in HIST_MANIFEST,
                      obs in SUM_MANIFEST)
        # seed our buffer objects from additional_day_stats
        if additional_day_stats:
            for obs in [f for f in additional_day_stats if f in MANIFEST]:
                if obs not in self:
                    seed_func = seed_functions.get(obs, RtcrBuffer.seed_scalar)
                    seed_func(self, additional_day_stats[obs], obs, obs in HILO_MANIFEST,
                              obs in HIST_MANIFEST, obs in SUM_MANIFEST)
        self.unit_system = unit_system
        self.last_windSpeed_ts = None
        self.windrun = self.seed_windrun(day_stats)

    def seed_scalar(self, stats, obs_type, hist, sum):
        """Seed a scalar buffer."""

        self[obs_type] = init_dict.get(obs_type, ScalarBuffer)(stats=stats,
                                                               history=hist,
                                                               sum=sum)

    def seed_vector(self, stats, obs_type, hist, sum):
        """Seed a vector buffer."""

        self[obs_type] = init_dict.get(obs_type, VectorBuffer)(stats=stats,
                                                               history=True,
                                                               sum=True)

    def seed_windrun(self, day_stats):
        """Seed day windrun."""

        if 'windSpeed' in day_stats:
            # The wsum field hold the sum of (windSpeed * interval in seconds)
            # for today so we can calculate windrun from wsum - just need to
            # do a little unit conversion and scaling

            # The day_stats units may be different to our buffer unit system so
            # first convert the wsum value to a km_per_hour based value (the
            # wsum 'units' are a distance but we can use the group_speed
            # conversion to convert to a km_per_hour based value)
            # first get the day_stats windSpeed unit and unit group
            (unit, group) = weewx.units.getStandardUnitType(day_stats.unit_system,
                                                            'windSpeed')
            # now express wsum as a 'group_speed' Valuetuple
            _wr_vt = ValueTuple(day_stats['windSpeed'].wsum, unit, group)
            # convert it to a 'km_per_hour' based value
            _wr_km = convert(_wr_vt, 'km_per_hour').value
            # but _wr_km was based on wsum which was based on seconds not hours
            # so we need to divide by 3600 to get our real windrun in km
            windrun = _wr_km/3600.0
        else:
            windrun = 0.0
        return windrun


    def add_packet(self, packet):
        """Add a packet to the buffer."""

        packet = weewx.units.to_std_system(packet, self.unit_system)
        if packet['dateTime'] is not None:
            for obs in [f for f in packet if f in MANIFEST]:
                add_func = add_functions.get(obs, RtcrBuffer.add_value)
                add_func(self, packet, obs, obs in HILO_MANIFEST,
                         obs in HIST_MANIFEST, obs in SUM_MANIFEST)

    def add_value(self, packet, obs_type, hilo, hist, sum):
        """Add a value to the buffer."""

        if obs_type not in self:
            self[obs_type] = init_dict.get(obs_type, ScalarBuffer)(stats=None,
                                                                   history=hist,
                                                                   sum=sum)
        self[obs_type]._add_value(packet[obs_type], packet['dateTime'],
                                  hilo, hist, sum)

    def add_wind_value(self, packet, obs_type, hilo, hist, sum):
        """Add a wind value to the buffer."""

        # first add it as 'windSpeed' the scalar
        self.add_value(packet, obs_type, hilo, hist, sum)

        # update todays windrun
        if 'windSpeed' in packet:
            try:
                self.windrun += packet['windSpeed'] * (packet['dateTime'] - self.last_windSpeed_ts)/1000.0
            except TypeError:
                pass
            self.last_windSpeed_ts = packet['dateTime']

        if 'wind' not in self:
            self['wind'] = VectorBuffer(stats=None, history=True)
        self['wind']._add_value((packet.get('windSpeed'), packet.get('windDir')),
                                packet['dateTime'], False, True, False)

    def clean(self, ts):
        """Clean out any old obs from the buffer history."""

        for obs in HIST_MANIFEST:
            self[obs]['history_full'] = min([a.ts for a in self[obs]['history'] if a.ts is not None]) <= old_ts
            # calc ts of oldest sample we want to retain
            oldest_ts = ts - MAX_AGE
            # remove any values older than oldest_ts
            self[obs]['history'] = [s for s in self[obs]['history'] if s.ts > oldest_ts]

    def start_of_day_reset(self):
        """Reset our buffer stats at the end of an archive period.

        Reset our hi/lo data but don't touch the history, it might need to be
        kept longer than the end of the archive period.
        """

        for obs in MANIFEST:
            self[obs].day_reset()

    def nineam_reset(self):
        """Reset our buffer stats at the end of an archive period.

        Reset our hi/lo data but don't touch the history, it might need to be
        kept longer than the end of the archive period.
        """

        for obs in SUM:
            self[obs].nineam_reset()


#===============================================================================
#                            Configuration dictionaries
#===============================================================================

init_dict = ListOfDicts({'wind' : VectorBuffer})
add_functions = ListOfDicts({'windSpeed': RtcrBuffer.add_wind_value})
seed_functions = ListOfDicts({'wind': RtcrBuffer.seed_vector})


# ============================================================================
#                              class ObsTuple
# ============================================================================


# A observation during some period can be represented by the value of the
# observation and the time at which it was observed. This can be represented
# in a 2 way tuple called an obs tuple. An obs tuple is useful because its
# contents can be accessed using named attributes.
#
# Item   attribute   Meaning
#    0    value      The observed value eg 19.5
#    1    ts         The epoch timestamp that the value was observed
#                    eg 1488245400
#
# It is valid to have an observed value of None.
#
# It is also valid to have a ts of None (meaning there is no information about
# the time the was was observed.

class ObsTuple(tuple):

    def __new__(cls, *args):
        return tuple.__new__(cls, args)

    @property
    def value(self):
        return self[0]

    @property
    def ts(self):
        return self[1]


# ============================================================================
#                            Class CachedPacket
# ============================================================================


class CachedPacket():
    """Class to cache loop packets.

    The purpose of the cache is to ensure that necessary fields for the
    generation of clientraw.txt are continuousl available on systems whose
    station emits partial packets. The key requirement is that the field
    exists, the value (numerical or None) is handled by method calculate().
    Method calculate() could be refactored to deal with missing fields, but
    this would result in overly complex code in method calculate().

    The cache consists of a dictionary of value, timestamp pairs where
    timestamp is the timestamp of the packet when obs was last seen and value
    is the value of the obs at that time. None values may be cached.

    A cached loop packet may be obtained by calling the get_packet() method.
    """

    # These fields must be available in every loop packet read from the
    # cache.
    OBS = ["cloudbase", "windDir", "windrun", "inHumidity", "outHumidity",
           "barometer", "radiation", "rain", "rainRate","windSpeed",
           "appTemp", "dewpoint", "heatindex", "humidex", "inTemp",
           "outTemp", "windchill", "UV"]

    def __init__(self, rec):
        """Initialise our cache object.

        The cache needs to be initialised to include all of the fields required
        by method calculate(). We could initialise all field values to None
        (method calculate() will interpret the None values to be '0' in most
        cases). The results may be misleading. We can get ballpark values for
        all fields by priming them with values from the last archive record.
        As the archive may have many more fields than rtcr requires, only prime
        those fields that rtcr requires.

        This approach does have the drawback that in situations where the
        archive unit system is different to the loop packet unit system the
        entire loop packet will be converted each time the cache is updated.
        This is inefficient.
        """

        self.cache = dict()
        # if we have a dateTime field in our record source use that otherwise
        # use the current system time
        _ts = rec['dateTime'] if 'dateTime' in rec else int(time.time() + 0.5)
        # only prime those fields in CachedPacket.OBS
        for _obs in CachedPacket.OBS:
            if _obs in rec and 'usUnits' in rec:
                # only add a value if it exists and we know what units its in
                self.cache[_obs] = {'value': rec[_obs], 'ts': _ts}
            else:
                # otherwise set it to None
                self.cache[_obs] = {'value': None, 'ts': _ts}
        # set the cache unit system if known
        self.unit_system = rec['usUnits'] if 'usUnits' in rec else None

    def update(self, packet, ts):
        """Update the cache from a loop packet.

        If the loop packet uses a different unit system to that of the cache
        then convert the loop packet before adding it to the cache. Update any
        previously seen cache fields and add any loop fields that have not been
        seen before.
        """

        if self.unit_system is None:
            self.unit_system = packet['usUnits']
        elif self.unit_system != packet['usUnits']:
            packet = weewx.units.to_std_system(packet, self.unit_system)
        for obs in [x for x in packet if x not in ['dateTime', 'usUnits']]:
            if packet[obs] is not None:
                self.cache[obs] = {'value': packet[obs], 'ts': ts}

    def get_value(self, obs, ts, max_age):
        """Get an obs value from the cache.

        Return a value for a given obs from the cache. If the value is older
        than max_age then None is returned.
        """

        if obs in self.cache and ts - self.cache[obs]['ts'] <= max_age:
            return self.cache[obs]['value']
        return None

    def get_packet(self, ts=None, max_age=600):
        """Get a loop packet from the cache.

        Resulting packet may contain None values.
        """

        if ts is None:
            ts = int(time.time() + 0.5)
        packet = {'dateTime': ts, 'usUnits': self.unit_system}
        for obs in self.cache:
            packet[obs] = self.get_value(obs, ts, max_age)
        return packet


# ============================================================================
#                            Utility Functions
# ============================================================================


def calc_trend(obs_type, now_vt, db_manager, then_ts, grace):
    """ Calculate change in an observation over a specified period.

    Inputs:
        obs_type:   database field name of observation concerned
        now_vt:     value of observation now (ie the finishing value)
        db_manager: manager to be used
        then_ts:    timestamp of start of trend period
        grace:      the largest difference in time when finding the then_ts
                    record that is acceptable

    Returns:
        Change in value over trend period. Can be positive, 0, negative or
        None. Result will be in 'group' units.
    """

    result = None
    if now_vt.value is not None:
        then_record = db_manager.getRecord(then_ts, grace)
        if then_record is not None and obs_type in then_record:
            then_vt = weewx.units.as_value_tuple(then_record, obs_type)
            then = convert(then_vt, now_vt.unit).value
            if then is not None:
                result = now_vt.value - then
    return result

def calc_wetbulb(Ta, RH, P):
    """Calculate wet bulb temperature.

        Uses formula:

        WB = (((0.00066 * P) * Ta) + ((4098 * E)/((Tdc + 237.7) ** 2) * Tdc))/
                 ((0.00066 * P) + (4098 * E)/((Tdc + 237.7) ** 2))

        Where:
            P = pressure (in hPa)
            Ta = air temperature (in degree C)
            RH = relative humidity (in %)
            E = 6.11 * 10 ** (7.5 * Tdc/(237.7 + Tdc))
            Tdc = Ta - (14.55 + 0.114 * Ta) * (1 - (0.01 * RH)) -
                      ((2.5 + 0.007 * Ta) * (1 - (0.01 * RH))) ** 3 -
                      (15.9 + 0.117 * Ta) * (1 - (0.01 * RH)) ** 14

        Input:
            Ta: temperature in Celsius
            RH: humidity in %
            P:  pressure in hPa

        Returns:    Wet bulb in degree C. Can be None.
    """

    if Ta is None or RH is None or P is None:
        return None
    Tdc = Ta - (14.55 + 0.114 * Ta) * (1 - (0.01 * RH)) - ((2.5 + 0.007 * Ta) * (1 - (0.01 * RH))) ** 3 - (15.9 + 0.117 * Ta) * (1 - (0.01 * RH)) ** 14
    E = 6.11 * 10 ** (7.5 * Tdc / (237.7 + Tdc))
    WB = (((0.00066 * P) * Ta) + ((4098 * E) / ((Tdc + 237.7) ** 2) * Tdc)) / ((0.00066 * P) + (4098 * E) / ((Tdc + 237.7) ** 2))
    return WB

