"""
This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

                     Installer for Realtime Clientraw

Version: 0.3.7                                        Date: 31 August 2023

Revision History
    31 August 2023      v0.3.7
        - comment out rtcr_path config option so that default (HTML_ROOT) is
          used for new installs
        - tidied up rtcr_path comments
    24 March 2023       v0.3.6
        -   config for installer is now derived from a multiline string for
            easy modification of config settings and to allow embedded comments
            in installed config stanzas
    22 January 2023     v0.3.5
        - no change, bump version only
    3 April 2022        v0.3.4
        - no change, bump version only
    7 February 2022     v0.3.3
        - no change, bump version only
    25 November 2021    v0.3.2
        - no change, bump version only
    13 May 2021         v0.3.0
        - no change, bump version only
    9 March 2020        v0.2.3
        - no change, bump version only
    1 March 2020        v0.2.2
        - no change, bump version only
    22 June 2019         v0.2.1
        - fix some pycharm complaints
        - reformat top of file comments
    19 March 2017       v0.2.0
        - no change, bump version only
    7 March 2017        v0.1.0
        - initial implementation
"""

# python imports
import configobj
from distutils.version import StrictVersion
from setup import ExtensionInstaller

# import StringIO, use six.moves due to python2/python3 differences
from six.moves import StringIO

# WeeWX imports
import weewx

REQUIRED_VERSION = "4.5.0"
RTCR_VERSION = "0.3.7"

# Multi-line config string, makes it easier to include comments. Needs to be
# explicitly set as unicode or python2 StringIO complains.
rtcr_config = u"""
[RealtimeClientraw]

    # Path to clientraw.txt. Can be an absolute or relative path. Relative
    # paths are relative to HTML_ROOT. Optional, default setting is to use
    # HTML_ROOT.
    # rtcr_path = /home/weewx/public_html

    # If using an external website, configure remote_server_url to point to 
    # the post_clientraw.php script on your website like:
    #   remote_server_url = http://your.website.com/post_clientraw.php
    #
    # To disable or use the webserver on this system, leave the entry 
    # commented out or blank.
    # remote_server_url = http://your.website.com/post_clientraw.php

    # min_interval sets the minimum clientraw.txt generation interval. 
    # 10 seconds is recommended for all Saratoga template users. Default 
    # is 0 seconds.
    min_interval = 10

    # Python date-time format strings. Format string codes as per 
    # https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes

    # Date format. Recommended entries are:
    #   date_format = %-m/%-d/%Y  # recommended for USA users
    #   date_format = %-d/%-m/%Y  # recommended for non-USA users
    date_format = %-d/%-m/%Y

    # Long format times (HMS). Recommended entries are:
    #   long_time_format = %-I:%M:%S_%p  # recommended for USA users
    #   long_time_format = %H:%M:%S  # recommended for non-USA users 
    long_time_format = %H:%M:%S

    # Short format times (HM). Recommended entries are:
    #   short_time_format = %-I:%M_%p  # recommended for USA users
    #   short_time_format = %H:%M  # recommended for non-USA users
    short_time_format = %H:%M
"""

# obtain our config string as a configobj dict
rtcr_dict = configobj.ConfigObj(StringIO(rtcr_config))


def loader():
    return RtcrInstaller()


class RtcrInstaller(ExtensionInstaller):
    def __init__(self):
        if StrictVersion(weewx.__version__) < StrictVersion(REQUIRED_VERSION):
            msg = "%s requires WeeWX %s or greater, found %s" % ('Rtcr ' + RTCR_VERSION,
                                                                 REQUIRED_VERSION,
                                                                 weewx.__version__)
            raise weewx.UnsupportedFeature(msg)
        super(RtcrInstaller, self).__init__(
            version=RTCR_VERSION,
            name='RTCR',
            description='WeeWX support for near realtime generation of a limited clientraw.txt.',
            author="Gary Roderick",
            author_email="gjroderick@gmail.com",
            report_services=['user.rtcr.RealtimeClientraw'],
            config=rtcr_dict,
            files=[('bin/user', ['bin/user/rtcr.py'])]
        )
