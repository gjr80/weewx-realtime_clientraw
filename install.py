"""
This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 2 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

                     Installer for Realtime Clientraw

Version: 0.2.2                                        Date: 1 March 2020

Revision History
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

import weewx

from distutils.version import StrictVersion
from setup import ExtensionInstaller

REQUIRED_VERSION = "3.4.0"
RTCR_VERSION = "0.2.2"


def loader():
    return RtcrInstaller()


class RtcrInstaller(ExtensionInstaller):
    def __init__(self):
        if StrictVersion(weewx.__version__) < StrictVersion(REQUIRED_VERSION):
            msg = "%s requires weeWX %s or greater, found %s" % ('Rtcr ' + RTCR_VERSION,
                                                                 REQUIRED_VERSION,
                                                                 weewx.__version__)
            raise weewx.UnsupportedFeature(msg)
        super(RtcrInstaller, self).__init__(
            version=RTCR_VERSION,
            name='Rtcr',
            description='WeeWX support for near realtime generation of a limited clientraw.txt.',
            author="Gary Roderick",
            author_email="gjroderick@gmail.com",
            report_services=['user.rtcr.RealtimeClientraw'],
            config={
                'RealtimeClientraw': {
                    'rtcr_path': '/home/weewx/public_html'
                }
            },
            files=[('bin/user', ['bin/user/rtcr.py'])]
        )
