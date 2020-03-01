# Realtime clientraw extension #

## Description ##

The *Realtime clientraw* extension is a WeeWX extension that generates a loop data based *clientraw.txt* file for near realtime updating of the [Saratoga Weather Website templates](http://saratoga-weather.org/wxtemplates/index.php "Free Weather Website Templates") dashboards.

**Note:** The Saratoga dashboards include the standard dashboard included in the Saratoga Weather Website templates and the so called Alternative dashboard. Use of the term *Saratoga dashboards* in this repository is taken to mean both the standard dashboard included in the Saratoga Weather Website templates and the so called Alternative dashboard.  

**Note:** Whilst *clientraw.txt* can be used for a number of purposes other than near realtime updates of the Saratoga dashboards, (eg updating Weather Display Live), the *Realtime clientraw* extension has been developed solely for updating the Saratoga dashboards. As such some *clientraw.txt* fields not used by the Saratoga dashboards have not been calculated and consequently the *Realtime clientraw* extension generated *clientraw.txt* may not be suitable for these other purposes. The initial comments in the *rtcr.py* file detail the *clientraw.txt* fields that are not calculated.

## Pre-Requisites ##

The *Realtime clientraw* extension requires WeeWX v3.4.0 or greater. Use of the *Realtime clientraw* extension with the Saratoga template requires the installation and configuration for use with WeeWX of the Saratoga templates.

## Installation ##

The *Realtime clientraw* extension can be installed manually or automatically using the *wee_extension* utility. The preferred method of installation is through the use of *wee_extension*.

**Note:**   Symbolic names are used below to refer to some file location on the WeeWX system. These symbolic names allow a common name to be used to refer to a directory that may be different from system to system. The following symbolic names are used below:

-   *$DOWNLOAD_ROOT*. The path to the directory containing the downloaded *Realtime clientraw* extension.
    
-   *$HTML_ROOT*. The path to the directory where WeeWX generated reports are saved. This directory is normally set in the *[StdReport]* section of *weewx.conf*. Refer to [where to find things](http://weewx.com/docs/usersguide.htm#Where_to_find_things "where to find things") in the WeeWX [User's Guide](http://weewx.com/docs/usersguide.htm "User's Guide to the WeeWX Weather System") for further information.
    
-   *$BIN_ROOT*. The path to the directory where WeeWX executables are located. This directory varies depending on WeeWX installation method. Refer to [where to find things](http://weewx.com/docs/usersguide.htm#Where_to_find_things "where to find things") in the WeeWX [User's Guide](http://weewx.com/docs/usersguide.htm "User's Guide to the WeeWX Weather System") for further information.

### Installation using the wee_extension utility ###

1.  Download the latest *Realtime clientraw* extension from the *Realtime clientraw* extension [releases page](https://github.com/gjr80/weewx-realtime_clientraw/releases) into a directory accessible from the WeeWX machine.

     
        wget -P $DOWNLOAD_ROOT https://github.com/gjr80/weewx-realtime_clientraw/releases/download/v0.2.2/rtcr-0.2.2.tar.gz

    where $DOWNLOAD_ROOT is the path to the directory where the *Realtime clientraw* extension is to be downloaded.  

2.  Stop WeeWX:

        sudo /etc/init.d/weewx stop

    or

        sudo service weewx stop

3.  Install the *Realtime clientraw* extension downloaded at step 1 using the *wee_extension* utility:

        wee_extension --install=$DOWNLOAD_ROOT/rtcr-0.2.2.tar.gz

    This will result in output similar to the following:

        Request to install '/var/tmp/rtcr-0.2.2.tar.gz'
        Extracting from tar archive /var/tmp/rtcr-0.2.2.tar.gz
        Saving installer file to /home/weewx/bin/user/installer/Rtcr
        Saved configuration dictionary. Backup copy at /home/weewx/weewx.conf.20170215124410
        Finished installing extension '/var/tmp/rtcr-0.2.2.tar.gz'

4.  Start WeeWX:

        sudo /etc/init.d/weewx start

    or

        sudo service weewx start

This will result in the *clientraw.txt* file being generated on receipt of each loop packet. A default installation will result in the generated *clientraw.txt* file being placed in the *$HTML_ROOT* directory. The *Realtime clientraw* extension installation can be further customized (eg file locations, frequency of generation etc) by referring to the *Realtime clientraw* extension wiki.

### Manual installation ###

1.  1.  Download the latest *Realtime clientraw* extension from the *Realtime clientraw* extension [releases page](https://github.com/gjr80/weewx-realtime_clientraw/releases) into a directory accessible from the WeeWX machine.

        wget -P $DOWNLOAD_ROOT https://github.com/gjr80/weewx-realtime_clientraw/releases/download/v0.2.2/rtcr-0.2.2.tar.gz

    where $DOWNLOAD_ROOT is the path to the directory where the *Realtime clientraw* extension is to be downloaded.  

2.  Unpack the extension as follows:

        tar xvfz rtcr-0.2.2.tar.gz

3.  Copy files from within the resulting directory as follows:

        cp rtcrd/bin/user/rtcr.py $BIN_ROOT/user
    
    replacing the symbolic name *$BIN_ROOT* with the nominal locations for your installation.

4.  Edit *weewx.conf*:

        vi weewx.conf

5.  In *weewx.conf*, modify the *[Engine] [[Services]]* section by adding the *RealtimeClientraw* service to the list of process services to be run:

        [Engine]
            [[Services]]
        
                report_services = weewx.engine.StdPrint, weewx.engine.StdReport, user.rtgd.RealtimeClientraw

6.  Stop then start WeeWX:

        sudo /etc/init.d/weewx stop
        sudo /etc/init.d/weewx start

    or

        sudo service weewx stop
        sudo service weewx start

This will result in the *clientraw.txt* file being generated on receipt of each loop packet. A default installation will result in the generated *clientraw.txt* file being placed in the *$HTML_ROOT* directory. The *Realtime clientraw* extension installation can be further customized (eg file locations, frequency of generation etc) by referring to the *Realtime clientraw* extension wiki.

## Support ##

General support issues may be raised in the Google Groups [weewx-user forum](https://groups.google.com/group/weewx-user "Google Groups weewx-user forum"). Specific bugs in the *Realtime clientraw* extension code should be the subject of a new issue raised via the [Issues Page](https://github.com/gjr80/weewx-realtime_clientraw/issues "Realtime clientraw extension Issues").
 
## Licensing ##

The *Realtime clientraw* extension is licensed under the [GNU Public License v3](https://github.com/gjr80/weewx-realtime_clientraw/blob/master/LICENSE "*Realtime clientraw* extension License").
