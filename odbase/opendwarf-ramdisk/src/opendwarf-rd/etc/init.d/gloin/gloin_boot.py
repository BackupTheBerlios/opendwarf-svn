#!/usr/bin/env python

import os
import sys
import time
import re
import ldap
import ldap.modlist as modlist
import syslog
import signal
from optparse import OptionParser


syslogprefix="gloin_boot: "
syslogident = "gloin_boot"

### colors ####

# ANSI COLORS
# Clear and reset Screen
CLEAR="c"
# Normal color
NORMAL="[0;39m"
# RED: Failure or error message
RED="[1;31m"
# GREEN: Success message
GREEN="[1;32m"
# YELLOW: Descriptions
YELLOW="[1;33m"
# BLUE: System mesages
BLUE="[1;34m"
# MAGENTA: Found devices or drivers
MAGENTA="[1;35m"
# CYAN: Questions
CYAN="[1;36m"
# BOLD WHITE: Hint
WHITE="[1;37m"

SUCCESS=" "+BLUE+"[ "+CYAN+"ok"+BLUE+" ]"+NORMAL
FAILED=" "+NORMAL+"[ "+RED+"fail"+NORMAL+" ]"


### end colors ####


def log_begin_msg(line, newline, endmark=""):
  if newline == True:
  	print " "+CYAN+"*"+NORMAL+" "+line+endmark
  else:
  	print " "+CYAN+"*"+NORMAL+" "+line+endmark,

def log_warn_msg (line, newline, endmark=""):
  if newline == True:
  	print " "+YELLOW+"*"+NORMAL+" "+line+endmark
  else:
	print " "+YELLOW+"*"+NORMAL+" "+line+endmark,

def log_error_msg (line, newline, endmark=""):
  if newline == True:
  	print " "+RED+"*"+NORMAL+" "+line+endmark
  else:
  	print " "+RED+"*"+NORMAL+" "+line+endmark,


def retrim(inputstr):

	inputstr = re.sub("^[^\w]+","",inputstr)
	inputstr = re.sub("[^\w]+$","",inputstr)

	return inputstr

	

def getLdapDn(ldapuri, ldapbase, ldapfilter, retrieve_attributes=None, scope=ldap.SCOPE_SUBTREE, timeout=0):

	l = ldap.initialize(ldapuri)
        l.bind_s('', '')


        result_set = []
	retrieve_attributes_value = {}


        dn = "empty"

        try:

                result_id = l.search(ldapbase, scope, ldapfilter, retrieve_attributes)

                while 1:

                        result_type, result_data = l.result(result_id, timeout)

                        if (result_data == []):
                                break
                        else:
                                if result_type == ldap.RES_SEARCH_ENTRY:
                                        result_set.append(result_data)

                if len(result_set) == 0:
                        syslog.syslog(syslogprefix+'No ldap results for '+ldapfilter)
			l.unbind_s()
                        return dn, retrieve_attributes_value

                for i in range(len(result_set)):
                        for entry in result_set[i]:
                                try:
                                        dn = entry[0]
					retrieve_attributes_value = entry[1]
	

                                except:
                                        pass
		l.unbind_s()

        except ldap.LDAPError, error_message:
		l.unbind_s()
		syslog.syslog(syslogprefix+' '+str(error_message))


        return dn, retrieve_attributes_value 

def getMyMac(interface):			

	macfinder = re.compile("([0-9A-F]{2}:){5}[0-9A-F]{2}")

	cmdIn, cmdOut, cmdErr = os.popen3('ifconfig '+interface)

	for line in cmdOut.readlines():
		temp = macfinder.search(line.upper())
		if temp:
			myMac = temp.group(0)

	return myMac	

def getConfigserverIP():

  try:
        filehandle = open("/etc/opendwarf/configserver")
        line = filehandle.readline()
        filehandle.close()
        line = retrim(line)
        line = re.sub("\n","",line)
        return line

  except IOError:
        return None

def getConfigserverMac(configserver):

	macfinder = re.compile("([0-9A-F]{2}:){5}[0-9A-F]{2}")

	configservermac="empty"

        arpfile = open("/proc/net/arp", "r")
	for line in arpfile.readlines():
		if line.count(configserver) > 0:
			configservermac = macfinder.search(line.upper()).group(0)
        arpfile.close()

	return configservermac

	

def getLdapBase():

        ldapbase = retrim(open('/etc/opendwarf/ldap.base','r').readlines()[0])

        return ldapbase


def main():

        master_image=False
        if os.path.exists(r'/opendwarf/config/identification.conf'):
		identification_file = open("/opendwarf/config/identification.conf", "r")
		type=retrim(identification_file.readline())
		if type == "master-image":
			master_image=True


	try:

	  if master_image == False:

		syslog.syslog(syslogprefix+' script got woken up.')
		log_begin_msg("launching "+syslogident, True)

		configserver = getConfigserverIP()

                if not configserver:
                        log_error_msg("searching configserver", False, FAILED)
			syslog.syslog(syslogprefix+' no configserver found.')	
                        sys.exit(1)

		ldapuri = "ldap://"+configserver+":389"
		ldapbase = getLdapBase()
		ldapfilter = ""

		interface="eth0"
		myMac = getMyMac(interface)
		#myMac = "00:19:D1:DD:EA:E1"

		ldapWantedDnAttributes=["ipHostNumber"]


		ldapfilter="(macAddress="+str(myMac)+")"

		retrievedAttributes = {}
		myDN, retrievedAttriubutes = getLdapDn(ldapuri, ldapbase, ldapfilter, ldapWantedDnAttributes)
		try:
			ip = retrievedAttriubutes["ipHostNumber"][0]
		except KeyError:
			ip = "empty"
		configserverMac = getConfigserverMac(configserver)
		ldapfilter="(macAddress="+str(configserverMac)+")"
		myConfigserverDN, configserverRetrievedAttriubutes = getLdapDn(ldapuri, ldapbase, ldapfilter, ldapWantedDnAttributes)

		if myDN == "empty":
                        log_error_msg("searching for my ldap entry", False, FAILED)
			raw_input("ERROR: check your Appliance ("+configserver+"), new clients creation service should be running. press ENTER to reboot.")
			os.system('init 6')




		clientIsInHwdOU = False
		myDNList = myDN.split(",")
		hostname = myDNList[0]
	        hostname = re.sub("cn=","",hostname)
		hostnamefile = open("/etc/hostname", "w")
		hostnamefile.write(hostname)
		hostnamefile.close()
		

		for dnpart in myDNList:
			ldapWantedDnAttributes=["description"]
			retrievedAttributes = {}
			ldapfilter="("+dnpart+")"
			myDN, retrievedAttriubutes = getLdapDn(ldapuri, ldapbase, ldapfilter, ldapWantedDnAttributes)
			try:
				ldapobjectdescription = retrievedAttriubutes["description"][0]
				if ldapobjectdescription == "new_clients_ou":
					clientIsInHwdOU = True	
			except KeyError:
				pass


		if clientIsInHwdOU == True:
			syslog.syslog(syslogprefix+' '+myMac+' '+'booting WITH hardwaredetection.')
                        log_begin_msg("client is in hardware detection OU.", True)
			os.system('/etc/init.d/gloin/gloin_hardware_detection.sh')
		else:

		   	try:
				ipsettings = configserverRetrievedAttriubutes["ipHostNumber"][0].split("/")
		   	except KeyError:
                        	log_error_msg("searching ldap for ip subnet settings", False, FAILED)
				raw_input("\n\nThe Appliance i have booted from does'nt have enough network settings. Please specify the network-settings for this Appliance ("+configserver+") in the following format:\n <ipadress>/<netmask>/<broadcast>/<gateway>\n\n This configuration change can be done with gosa in the IP-Address field of the Appliance.\n Press ENTER to reboot.")
				os.system('init 6')
			print retrievedAttriubutes	
			if ip == "empty":
                        	log_error_msg("searching ldap for static ip setting", False, FAILED)
				raw_input("\n\nPlease specify a IP-Address for this workstation (mac: "+myMac+") within gosa. Press ENTER to reboot.")
				os.system('init 6')
			mask = ipsettings[1]	
			broadcast = ipsettings[2]	
			gw = ipsettings[3]	

                        log_begin_msg("writing new network configuration file", False)
       	        	ifconfigfile = open("/etc/network/interfaces", "w")
			ifconfigfile.write("auto lo"+"\n")
			ifconfigfile.write("auto "+interface+"\n")
			ifconfigfile.write("iface lo inet loopback"+"\n")
			ifconfigfile.write("iface "+interface+" inet static"+"\n")	
			ifconfigfile.write("address "+ip+"\n")
			ifconfigfile.write("netmask "+mask+"\n")
			ifconfigfile.write("broadcast "+broadcast+"\n")
			ifconfigfile.write("gateway "+gw+"\n")
                	ifconfigfile.close()
			print SUCCESS

			os.system('/etc/init.d/gloin/gloin_net_stage2.sh')

			syslog.syslog(syslogprefix+' '+myMac+' '+'booting without hardwaredetection.')
			os.system('echo 1 > /etc/hwd')
			os.system ('/etc/init.d/gloin/gloin_loadmodules.py')
                        log_begin_msg("mouting /proc/bus/usb", True)
			os.system('mount /proc/bus/usb')
			os.system ('/etc/init.d/gloin/gloin_writexorg.py')
			

	  else:
		log_begin_msg("launching "+syslogident, True)

		hostname = "master-image"
		hostnamefile = open("/etc/hostname", "w")
		hostnamefile.write(hostname)
		hostnamefile.close()

		log_begin_msg("umounting ramdisk", True)
		os.system('umount /initrd')

		log_begin_msg("writing / fstab entry", True)
		os.system('echo "/dev/sda  / ext3     defaults        0       1" >> /etc/fstab')

		clientIsInHwdOU = True

		os.system('/etc/init.d/gloin/gloin_net_stage2.sh')
		os.system('echo 1 > /etc/hwd')
               # log_begin_msg("mouting /proc/bus/usb", True)
	#	os.system('mount /proc/bus/usb 2>/dev/null')

	

	except KeyboardInterrupt:
		print "Ctrl+C recognized."
		sys.exit(1)

if __name__=='__main__': main()
