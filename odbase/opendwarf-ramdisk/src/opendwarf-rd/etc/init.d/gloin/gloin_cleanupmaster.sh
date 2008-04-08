#!/bin/bash
. /etc/init.d/gloin/msg_colorizer.sh

setcolors

log_begin_msg "deleting /etc/opendwarf"
rm -rf /etc/opendwarf && echo "  $SUCCESS" || echo " failed "

log_begin_msg "deleting xorg.conf"
cat /dev/null > /etc/X11/xorg.conf && echo "  $SUCCESS" || echo " failed "

log_begin_msg "deleting debian network configurations"
cat /dev/null > /etc/network/interfaces && echo "  $SUCCESS" || echo " failed "

log_begin_msg "deleting opendwarf runlevel files"
cat /dev/null > /etc/runlevel.conf && echo "  $SUCCESS" || echo " failed "

log_begin_msg "deleting opendwarf init scripts"
rm -rf /etc/init.d/gloin && echo "  $SUCCESS" || echo " failed "


#log_begin_msg "umounting stuff"
#cd /
#umount /etc/network/run
#umount /tmp
#umount /var/lock
#umount /var/log
#umount /var/run
#umount /var/tmp
#umount /home
#umount /root
#mount -o remount,ro /initrd
#echo "  $SUCCESS"
