#!/bin/bash
. /etc/init.d/thinit/msg_colorizer.sh

setcolors

log_begin_msg "hardware detection done, rebooting in 10 seconds."
sleep 10
reboot >/dev/null 2>&1 && echo "  $SUCCESS" || echo " $FAILED  " 
