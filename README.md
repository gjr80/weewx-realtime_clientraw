# Realtime *clientraw* Extension

**Note:** If *clientraw.txt* is intended for use with the Saratoga Weather Website templates the [*WeeWX-Saratoga extension*](https://github.com/gjr80/weewx-saratoga) should be used rather than the *Realtime clientraw extension*. The *WeeWX-Saratoga extension* includes the *Realtime clientraw extension* as well as the generation of a number of other data files used by the Saratoga Weather Website templates.

The *Realtime clientraw extension* is a WeeWX extension that generates a loop data based *clientraw.txt* file for near realtime updating of the [Saratoga Weather Website templates](http://saratoga-weather.org/wxtemplates/index.php "Free Weather Website Templates") dashboards. *clientraw.txt* may also be used by some other applications for near realtime display of weather related data (eg updating Weather Display Live).

Unlike WeeWX template based generation of *clientraw.txt*, the *Realtime clientraw extension* uses a custom WeeWX service to generate a near realtime *clientraw.txt* based on loop packet data.  

**Note:** The Saratoga dashboards include the standard dashboard included in the Saratoga Weather Website templates and the so-called Alternate dashboard. Use of the term *Saratoga dashboards* in this repository is taken to mean both the standard dashboard included in the Saratoga Weather Website templates and the so-called Alternate dashboard.  

**Note:** Whilst *clientraw.txt* can be used for a number of purposes other than near realtime updates of the Saratoga dashboards, the *Realtime clientraw extension* has been developed solely for updating the Saratoga dashboards. As such some *clientraw.txt* fields not used by the Saratoga dashboards have not been populated and consequently the *Realtime clientraw extension* generated *clientraw.txt* may not be suitable for these other purposes. The initial comments in the *rtcr.py* file detail the *clientraw.txt* fields that are not populated.

**Note:** The *Realtime clientraw extension* generates *clientraw.txt* upon receipt of each loop packet. As such the definition of _near realtime_ is very much dependent on the period between successive loop packets. The period between successive loop packets is normally a limitation of either the station hardware or driver or both.


## Pre-Requisites

The *Realtime clientraw extension* requires WeeWX v4.5.0 or greater.


## Installation

The preferred method of installing the *Realtime clientraw extension* is using the WeeWX [*wee_extension* utility](http://weewx.com/docs/utilities.htm#wee_extension_utility). The *Realtime clientraw extension* can also be installed manually.

**Note:** Symbolic names are used below to refer to some file location on the WeeWX system. Symbolic names allow a common name to be used to refer to a directory that may be different from system to system. The following symbolic names are used below:

- *HTML_ROOT*. The path to the directory where WeeWX generated reports and images are located. This directory varies depending on WeeWX installation method and system or web server configuration.
    
- *BIN_ROOT*. The path to the directory where WeeWX executables are located. This directory varies depending on WeeWX installation method.

Refer to [where to find things](http://weewx.com/docs/usersguide.htm#Where_to_find_things) in the *WeeWX User's Guide* for further information.


### Installation using the *wee_extension* utility

1.  Download the latest *Realtime clientraw extension* from the *Realtime clientraw extension* [releases page](https://github.com/gjr80/weewx-realtime_clientraw/releases) into a directory accessible from the WeeWX machine:
     
        wget -P /var/tmp https://github.com/gjr80/weewx-realtime_clientraw/releases/download/v0.3.6/rtcr-0.3.6.tar.gz

    in this case the extension package will be downloaded to directory */var/tmp*.

1.  Stop WeeWX:

        sudo /etc/init.d/weewx stop

	or

        sudo service weewx stop

    or

        sudo systemctl stop weewx

1.  Install the *Realtime clientraw extension* downloaded at step 1 using the WeeWX *wee_extension* utility:

        wee_extension --install=/var/tmp/rtcr-0.3.6.tar.gz

    **Note:** Depending on your system/installation the above command may need to be prefixed with *sudo*.

    **Note:** Depending on your WeeWX installation the path to *wee_extension* may need to be provided, eg:

        /home/weewx/bin/wee_extension --install....

    This will result in output similar to the following:

        Request to install '/var/tmp/rtcr-0.3.6.tar.gz'
        Extracting from tar archive /var/tmp/rtcr-0.3.6.tar.gz
        Saving installer file to /home/weewx/bin/user/installer/Rtcr
        Saved configuration dictionary. Backup copy at /home/weewx/weewx.conf.20230515124410
        Finished installing extension '/var/tmp/rtcr-0.3.6.tar.gz'

    **Note:** If upgrading an existing *Realtime clientraw extension* installation any previous *Realtime clientraw extension* configuration information in *weewx.conf* will have been retained and upgraded as required. *wee_extension* will save a timestamped backup copy of the pre-upgrade *weewx.conf* as detailed in the *wee_extension* output, eg:
    
        Saved configuration dictionary. Backup copy at /home/weewx/weewx.conf.20230515124410

1.  Start WeeWX:

        sudo /etc/init.d/weewx start

	or

        sudo service weewx start

    or

        sudo systemctl start weewx

1.  This will result in the *clientraw.txt* file being generated on receipt of each loop packet. A default installation will result in the generated *clientraw.txt* file being placed in the *HTML_ROOT* directory.

1.  The *Realtime clientraw extension* installation can be further customized (eg file locations, frequency of generation etc) by referring to the *Realtime clientraw extension* wiki (to be written).


### Manual installation

1.  Download the latest *Realtime clientraw extension* from the *Realtime clientraw extension* [releases page](https://github.com/gjr80/weewx-realtime_clientraw/releases) into a directory accessible from the WeeWX machine:
     
        wget -P /var/tmp https://github.com/gjr80/weewx-realtime_clientraw/releases/download/v0.3.6/rtcr-0.3.6.tar.gz

    in this case the extension package will be downloaded to directory */var/tmp*.

1.  Unpack the extension as follows:

        tar xvfz /var/tmp/rtcr-0.3.6.tar.gz

1.  Copy files from within the resulting *rtcr* directory as follows:

        cp /var/tmp/rtcr/bin/user/rtcr.py BIN_ROOT/user
    
    replacing the symbolic name *BIN_ROOT* with the nominal locations for your installation.

1.  Edit *weewx.conf*:

        vi weewx.conf

1.  In *weewx.conf*, modify the *[Engine] [[Services]]* section by adding the *RealtimeClientraw* service to the list of report services to be run:

        [Engine]
            [[Services]]
                ....
                report_services = weewx.engine.StdPrint, weewx.engine.StdReport, user.rtgd.RealtimeClientraw

1.  Start WeeWX:

        sudo /etc/init.d/weewx start

	or

        sudo service weewx start

    or

        sudo systemctl start weewx

1.  This will result in the *clientraw.txt* file being generated on receipt of each loop packet. A default installation will result in the generated *clientraw.txt* file being placed in the *$HTML_ROOT* directory.

1.  The *Realtime clientraw extension* installation can be further customized (eg file locations, frequency of generation etc) by referring to the *Realtime clientraw extension* wiki (to be written).


## Support

General support issues may be raised in the Google Groups [weewx-user forum](https://groups.google.com/group/weewx-user "Google Groups weewx-user forum"). Specific bugs in the *Realtime clientraw extension* code should be the subject of a new issue raised via the [Issues Page](https://github.com/gjr80/weewx-realtime_clientraw/issues "Realtime clientraw extension Issues").
 
## Licensing

The *Realtime clientraw extension* is licensed under the [GNU Public License v3](https://github.com/gjr80/weewx-realtime_clientraw/blob/master/LICENSE "*Realtime clientraw* extension License").
