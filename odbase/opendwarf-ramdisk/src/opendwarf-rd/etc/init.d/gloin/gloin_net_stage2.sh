#!/bin/bash
. /etc/init.d/gloin/msg_colorizer.sh

setcolors

interface=`cat /etc/opendwarf/discoverd_interface`
log_begin_msg "reconfiguring network interface $interface" && echo
log_begin_msg "sending ifdown to $interface"
ifdown $interface >/dev/null 2>&1 && echo "  $SUCCESS" || echo " failed  "
log_begin_msg "killing dhclient for $interface"
killall dhclient >/dev/null 2>&1 && echo "  $SUCCESS" || echo " failed  "
killall dhclient3  >/dev/null 2>&1
sleep 2
log_begin_msg "sending ifup to $interface"
ifup $interface >/dev/null 2>&1 && echo "  $SUCCESS" || echo " failed  "
