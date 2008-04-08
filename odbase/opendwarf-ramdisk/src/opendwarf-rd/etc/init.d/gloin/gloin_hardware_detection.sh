#!/bin/bash
. /etc/init.d/gloin/msg_colorizer.sh

setcolors

log_begin_msg "detecting network modules"
hwdetect --show-net > /tmp/hwd.txt 2>/dev/null && echo "  $SUCCESS" || echo " $FAILED  "

log_begin_msg "detecting sound modules"
hwdetect --show-sound >> /tmp/hwd.txt 2>/dev/null && echo "  $SUCCESS" || echo " $FAILED  "

log_begin_msg "detecting usb modules"
hwdetect --show-usb >> /tmp/hwd.txt 2>/dev/null && echo "  $SUCCESS" || echo " $FAILED  "

log_begin_msg "detecting agp modules"
hwdetect --show-agp >> /tmp/hwd.txt 2>/dev/null && echo "  $SUCCESS" || echo " $FAILED  "

log_begin_msg "detecting input modules"
hwdetect --show-input >> /tmp/hwd.txt 2>/dev/null && echo "  $SUCCESS" || echo " $FAILED  "

log_begin_msg "detecting remaining modules"
hwdetect --show-other >> /tmp/hwd.txt 2>/dev/null && echo "  $SUCCESS" || echo " $FAILED  "

log_begin_msg "running hwsetup"
hwsetup >/dev/null 2>&1 && echo "  $SUCCESS" || echo " $FAILED  "

echo -n "do you want to use a wizard to configure X11 settings? [yes], no: "
read -e XWIZARD

if [ "$XWIZARD" == "no" ]; then
	
	/usr/sbin/dpkg-reconfigure xserver-xorg -p critical >/dev/null 2>&1 && echo "  $SUCCESS" || echo " $FAILED  "
else
	/usr/sbin/dpkg-reconfigure xserver-xorg 
fi

/etc/init.d/syslog-ng stop >/dev/null 2>&1
/etc/init.d/syslog-ng start >/dev/null 2>&1

log_begin_msg "writing detected informations to ldap"
/etc/init.d/gloin/gloin_post_to_durin.py && echo "  $SUCCESS" || echo " $FAILED  "

sleep 10

log_begin_msg "rebooting to configured mode."
reboot >/dev/null 2>&1 && echo "  $SUCCESS" || echo " $FAILED  "
