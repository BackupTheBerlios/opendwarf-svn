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


syslogprefix="gloin_writexorg: "
syslogident = "gloin_writexorg"

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

def log_star():
  print WHITE+"*"+NORMAL,

def log_redstar():
  print RED+"*"+NORMAL,


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

        except ldap.LDAPError, error_message:
		l.unbind_s()
                print error_message

	l.unbind_s()

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

def getLdapBase():

        ldapbase = retrim(open('/etc/opendwarf/ldap.base','r').readlines()[0])

        return ldapbase



def main():

	try:

		syslog.syslog(syslogprefix+'syslogident script got woken up.')
		log_begin_msg("launching "+syslogident, True)

		detectedKernelModulesFile = "/tmp/hwd.txt"	
		xorgconfFile ="/etc/X11/xorg.conf"
	
		configserver = getConfigserverIP()


		if not configserver:
			log_error_msg("searching configserver", False, FAILED)
			sys.exit(1)

	
		ldapuri = "ldap://"+configserver+":389"
		ldapbase = getLdapBase()
		ldapfilter = "(description=/etc/X11/xorg.conf)"


		ldapWantedDnAttributes=["FAIscript"]

		retrievedAttributes = {}

		myDN, retrievedAttriubutes = getLdapDn(ldapuri, ldapbase, ldapfilter, ldapWantedDnAttributes)
		xorgConfTemplate = retrievedAttriubutes["FAIscript"]	


		interface="eth0"
		myMac = getMyMac(interface)

		ldapWantedDnAttributes=["gotoXResolution","gotoXDriver","gotoXColordepth", "gotoXHsync", "gotoXVsync", "gotoXMouseType", "gotoXMouseport", "gotoXKbLayout", "gotoXKbModel", "gotoXKbVariant"]


		ldapfilter="(macAddress="+str(myMac)+")"
		retrievedAttributes = {}
		myDN, retrievedAttriubutes = getLdapDn(ldapuri, ldapbase, ldapfilter, ldapWantedDnAttributes)

		myXorgAttributes = retrievedAttriubutes 

		xorgConf = ""
		log_begin_msg("writing xorg.conf ", False)
		for line in xorgConfTemplate:
			xorgConf = xorgConf+line	
			log_star()

		xorgConf=re.sub("\$gotoXResolution\$",myXorgAttributes["gotoXResolution"][0],xorgConf)
		log_redstar()
		xorgConf=re.sub("\$gotoXDriver\$",myXorgAttributes["gotoXDriver"][0],xorgConf)
		log_redstar()
		xorgConf=re.sub("\$gotoXColordepth\$",myXorgAttributes["gotoXColordepth"][0],xorgConf)
		log_redstar()
		xorgConf=re.sub("\$gotoXHsync\$",myXorgAttributes["gotoXHsync"][0],xorgConf)
		log_redstar()
		xorgConf=re.sub("\$gotoXVsync\$",myXorgAttributes["gotoXVsync"][0],xorgConf)
		log_redstar()
		xorgConf=re.sub("\$gotoXMouseType\$",myXorgAttributes["gotoXMouseType"][0],xorgConf)
		log_redstar()
		xorgConf=re.sub("\$gotoXMouseport\$",myXorgAttributes["gotoXMouseport"][0],xorgConf)
		log_redstar()
		xorgConf=re.sub("\$gotoXKbLayout\$",myXorgAttributes["gotoXKbLayout"][0],xorgConf)
		log_redstar()
		xorgConf=re.sub("\$gotoXKbModel\$",myXorgAttributes["gotoXKbModel"][0],xorgConf)
		log_redstar()
		xorgConf=re.sub("\$gotoXKbVariant\$",myXorgAttributes["gotoXKbVariant"][0],xorgConf)
		log_redstar()

		xorgConf=xorgConf.split("\n")

                xorgfilehandle = open("/etc/X11/xorg.conf", "w")

		for line in xorgConf:
			xorgfilehandle.write(line+"\n")
		xorgfilehandle.close()

		print SUCCESS


	except KeyboardInterrupt:
		print "Ctrl+C recognized."
		sys.exit(1)

if __name__=='__main__': main()
