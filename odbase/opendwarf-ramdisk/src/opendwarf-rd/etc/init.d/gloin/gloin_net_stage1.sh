#!/bin/bash
. /etc/init.d/gloin/msg_colorizer.sh

setcolors

log_begin_msg "configuring loopback interface lo"
/sbin/ifup lo >/dev/null 2>&1 && echo "  $SUCCESS" || echo " failed "

interface=`cat /etc/opendwarf/discoverd_interface`
log_begin_msg "configuring network interface $interface"
/sbin/dhclient $interface >/dev/null 2>&1 && echo "  $SUCCESS" || echo " failed  "
