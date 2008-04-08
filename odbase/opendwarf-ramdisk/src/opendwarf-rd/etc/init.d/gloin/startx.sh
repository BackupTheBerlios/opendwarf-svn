#!/bin/bash
hwd=`cat /etc/hwd 2>/dev/null `
if [ "$hwd" == "1" ]; then
	/usr/bin/startx
fi
