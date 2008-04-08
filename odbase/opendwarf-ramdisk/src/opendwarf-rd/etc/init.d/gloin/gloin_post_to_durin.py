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


syslogprefix="gloin_post_to_durin: "
syslogident = "gloin_post_to_durin"

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
		log_error_msg("ldap error:"+str(error_message), True)

	l.unbind_s()

        return dn, retrieve_attributes_value 

def addXorgAttributes(ldapuri, ldapbase, ldapwriteuser, ldapwritepassword, myDN, myXorgAttrs, old_attrs):

        l = ldap.initialize(ldapuri)
        l.simple_bind_s(ldapwriteuser, ldapwritepassword)

        ldif = modlist.modifyModlist(old_attrs,myXorgAttrs)

        try:
                l.modify_s(myDN,ldif)
        except ldap.LDAPError, error_message:
		log_error_msg("ldap error (add xorg attributes):"+str(error_message), True)

        l.unbind_s()

def addMyKernelModules(ldapuri, ldapbase, ldapwriteuser, ldapwritepassword, myDN, myKernelModules, old_attrs):

	l = ldap.initialize(ldapuri)
	l.simple_bind_s(ldapwriteuser, ldapwritepassword)

	attrs = {}

	attrs['gotoModules'] = myKernelModules	

	ldif = modlist.modifyModlist(old_attrs,attrs)

	try:
		l.modify_s(myDN,ldif)	
	except ldap.LDAPError, error_message:
		log_error_msg("ldap error (add kernel modules):"+str(error_message), True)

	l.unbind_s()

def addNicAttributes(ldapuri, ldapbase, ldapwriteuser, ldapwritepassword, myDN, myNicAttributes, old_attrs):

        l = ldap.initialize(ldapuri)
        l.simple_bind_s(ldapwriteuser, ldapwritepassword)

	attrs = myNicAttributes

        ldif = modlist.modifyModlist(old_attrs,attrs)

        try:
                l.modify_s(myDN,ldif)
        except ldap.LDAPError, error_message:
		log_error_msg("ldap error (add nic attributes):"+str(error_message), True)

        l.unbind_s()
	


def getMyMac(interface):			

	macfinder = re.compile("([0-9A-F]{2}:){5}[0-9A-F]{2}")

	cmdIn, cmdOut, cmdErr = os.popen3('ifconfig '+interface)

	for line in cmdOut.readlines():
		temp = macfinder.search(line.upper())
		if temp:
			myMac = temp.group(0)

	return myMac	

# should return dictionary with goto X attributes 
# graphics:	gotoXDriver, gotoXResoultion, gotoXColordepth
# monitor:	gotoXHsync, gotoXVsync
# mouse:	gotoXMouseType, gotoXMouseport
# keyboard:	gotoXKbLayout, gotoXKbModel, gotoXKbVariant 
def parseXorgConfigFile(file):

	# suck whole xorg.conf to an \n delim. string
	wholexorgconf = ""
	try:
		filehandle = open(file)
		while 1:
			line = filehandle.readline()
			if not line:
				break

			if not re.search("^$",line):
				if not re.search("^#",line):
					wholexorgconf=wholexorgconf+line

		filehandle.close()
	except IOError:
        	attrs = {}
		return attrs



	# regexp which matches anything between ServerLayout start and end, ServerLayout is needed for mouse and keyboard
	serverlayoutSectionRegExp = 'Section "ServerLayout"(.*?)EndSection'

	# regexp which matches anything between Screen start and end
	screenSectionRegExp = 'Section "Screen"(.*?)EndSection'
	
	# regexp which matches anything between 2 douple quotes
	betweenDoupleQoutesRegExp = '"(.*?)"'

	# compile the regexp's
	screenSectionSnipper = re.compile(screenSectionRegExp, re.DOTALL)
	betweenDoupleQoutesSnipper = re.compile(betweenDoupleQoutesRegExp, re.DOTALL)
	serverlayoutSectionSnipper = re.compile(serverlayoutSectionRegExp, re.DOTALL)

	# suck the Screen section in an array
	screensection = screenSectionSnipper.search(wholexorgconf)
	screensection = screensection.group(1)
	screensection = screensection.split("\n")

	# suck the ServerLayout section in an array
	serverlayoutsection = serverlayoutSectionSnipper.search(wholexorgconf) 
	serverlayoutsection = serverlayoutsection.group(1)

	# "checked out" serverlayout section removing it from wholexorgconf to make it easier to get input devices	
	wholexorgconf=re.sub(serverlayoutsection,"",wholexorgconf)

	serverlayoutsection = serverlayoutsection.split("\n")


	gcard_section=""
	monitor_section=""
	defaultdepth=""
	mouse_section=""
	keyboard_section=""

	# loop through the screensection "line by line" and look for Device (graphics card) Monitor and the default Color Depth
	for line in screensection:
		if line.count("Device") > 0:
			gcard_section=line
			gcard_section = betweenDoupleQoutesSnipper.search(gcard_section).group(1)
			gcard_section = re.sub("\[","\\[",gcard_section)
			gcard_section = re.sub("\]","\\]",gcard_section)
		if line.count("Monitor") > 0:
			monitor_section=line
			monitor_section = betweenDoupleQoutesSnipper.search(monitor_section).group(1)
		if line.count("DefaultDepth") > 0:
			defaultdepth=re.sub("DefaultDepth","",line)
			defaultdepth = retrim(defaultdepth) 
		if line.count("DefaultColorDepth") > 0:
			defaultdepth=re.sub("DefaultColorDepth","",line)
			defaultdepth = retrim(defaultdepth)

	# loop through the serverlayoutsection "line by line" and look for InputDevice ouse=Mouse eboard=Keyboard
	for line in serverlayoutsection:
		if line.count("InputDevice") > 0:
			if line.count("ouse") > 0:	 
					mouse_section=line
					mouse_section=re.sub("InputDevice","",mouse_section)
					mouse_section=retrim(mouse_section)
					mouse_section=mouse_section.split("\"")
					for mousestr in mouse_section:
						if mousestr.count("Core") == 0:
							if mousestr.count("ouse") > 0:
								mouse_section = retrim(mousestr)
					
			if line.count("eyboard") > 0:
					keyboard_section=line
					keyboard_section=re.sub("InputDevice","",keyboard_section)
					keyboard_section=retrim(keyboard_section)
					keyboard_section=keyboard_section.split("\"")
					for keybstr in keyboard_section:
						if keybstr.count("Core") == 0:
							if keybstr.count("eyboard") > 0:
								keyboard_section = retrim(keybstr)


	# build new regexp with the string from the searches above	

	gcardSectionRegExp = gcard_section+'(.*?)EndSection'
	gcardSectionSnipper = re.compile(gcardSectionRegExp, re.DOTALL)
	gcard_section = gcardSectionSnipper.search(wholexorgconf).group(1)

	monitorSectionRegExp = monitor_section+'(.*?)EndSection'
	monitorSectionSnipper = re.compile(monitorSectionRegExp, re.DOTALL)
	monitor_section = monitorSectionSnipper.search(wholexorgconf).group(1)

	mouseSectionRegExp = mouse_section+'(.*?)EndSection'
	mouseSectionSnipper = re.compile(mouseSectionRegExp, re.DOTALL)
	mouse_section = mouseSectionSnipper.search(wholexorgconf).group(1)

	keyboardSectionRegExp = keyboard_section+'(.*?)EndSection'
	keyboardSectionSnipper = re.compile(keyboardSectionRegExp, re.DOTALL)
	keyboard_section = keyboardSectionSnipper.search(wholexorgconf).group(1)

	if not defaultdepth:
		gotoXColordepth = "16"
	else:
		gotoXColordepth = defaultdepth


        # suck the sections in an array
        keyboard_section = keyboard_section.split("\n")
        mouse_section = mouse_section.split("\n")
        monitor_section = monitor_section.split("\n")
        gcard_section = gcard_section.split("\n")

	gotoXKbVariant=""
	gotoXKbModel=""
	gotoXKbLayout=""
	for line in keyboard_section:
		if line.count("XkbVariant") > 0:
			gotoXKbVariant = line.split("XkbVariant")[1]
		if line.count("XkbModel") > 0:
			gotoXKbModel = line.split("XkbModel")[1]
		if line.count("XkbLayout") > 0:
			gotoXKbLayout = line.split("XkbLayout")[1]
		



	gotoXKbVariant = re.sub("\"","",gotoXKbVariant)
	gotoXKbVariant = re.sub("\n","",gotoXKbVariant)
	gotoXKbVariant = retrim(gotoXKbVariant)

	gotoXKbModel = re.sub("\"","",gotoXKbModel)
	gotoXKbModel = re.sub("\n","",gotoXKbModel)
	gotoXKbModel = retrim(gotoXKbModel)

	gotoXKbLayout = re.sub("\"","",gotoXKbLayout)
	gotoXKbLayout = re.sub("\n","",gotoXKbLayout)
	gotoXKbLayout = retrim(gotoXKbLayout)

	gotoXMouseType=""
	gotoXMouseport=""

        for line in mouse_section:
                if line.count("Protocol") > 0:
                        gotoXMouseType = line.split("Protocol")[1]
                if line.count("Device") > 0:
                        gotoXMouseport = line.split("Device")[1]

	gotoXMouseType = re.sub("\"","",gotoXMouseType)
	gotoXMouseType = re.sub("\n","",gotoXMouseType)
	gotoXMouseType = retrim(gotoXMouseType)

	gotoXMouseport = re.sub("\"","",gotoXMouseport)
	gotoXMouseport = re.sub("\n","",gotoXMouseport)
	gotoXMouseport = retrim(gotoXMouseport)
	gotoXMouseport = "/"+gotoXMouseport

	gotoXHsync=""
	gotoXVsync=""
        for line in monitor_section:
                if line.count("HorizSync") > 0:
                         gotoXHsync = line.split("HorizSync")[1]
                if line.count("VertRefresh") > 0:
                         gotoXVsync = line.split("VertRefresh")[1]

	

	gotoXVsync = re.sub("\"","",gotoXVsync)
	gotoXVsync = re.sub("\n","",gotoXVsync)
	gotoXVsync = gotoXVsync.split("#")[0]
	gotoXVsync = retrim(gotoXVsync)

	gotoXHsync = re.sub("\"","",gotoXHsync)
	gotoXHsync = re.sub("\n","",gotoXHsync)
	gotoXHsync = gotoXHsync.split("#")[0]
	gotoXHsync = retrim (gotoXHsync)

	gotoXDriver=""
        for line in gcard_section:
                if line.count("Driver") > 0:
                        gotoXDriver = line.split("Driver")[1]

	gotoXDriver = re.sub("\"","",gotoXDriver)
	gotoXDriver = re.sub("\n","",gotoXDriver)
	gotoXDriver = retrim(gotoXDriver)


	gotoXResolution=""	

	screenSubSectionRegexp = 'SubSection "Display"(.*?)EndSubSection'
	screenSubSectionSnipper = re.compile(screenSubSectionRegexp, re.DOTALL)
	subsections = screenSubSectionSnipper.findall(wholexorgconf)

	subsectiondefaultColorDepth = ""
	for i in range(len(subsections)):
		 local_subsection = subsections[i].split("\n")
		 for line in local_subsection:
			if line.count("Depth") > 0:
				local_depth = line.split("Depth")[1]
				local_depth = re.sub("\"","",local_depth)
			        local_depth = re.sub("\n","",local_depth)
				local_depth = retrim(local_depth)
				
				if local_depth == gotoXColordepth:
					subsectiondefaultColorDepth=local_subsection
	gotoXResoultion=""	
	
	for line in subsectiondefaultColorDepth:
		if line.count("Modes") > 0:
			resolutions = line
			resolutions = re.sub("Modes","",resolutions)
			resolutions = retrim(resolutions)
			resolutions = resolutions.split(" ")
			gotoXResolution=resolutions[0]  	

	gotoXResolution = retrim(gotoXResolution)

        attrs = {}

        attrs['gotoXDriver'] = gotoXDriver
        attrs['gotoXResolution'] = gotoXResolution
        attrs['gotoXColordepth'] = gotoXColordepth
        attrs['gotoXHsync'] = gotoXHsync
        attrs['gotoXVsync'] = gotoXVsync
        attrs['gotoXMouseType'] = gotoXMouseType
        attrs['gotoXMouseport'] = gotoXMouseport
        attrs['gotoXKbLayout'] = gotoXKbLayout
        attrs['gotoXKbModel'] = gotoXKbModel
        attrs['gotoXKbVariant'] = gotoXKbVariant

	return attrs
	


	
def parseDetectedKernelModulesFile(file):

	allmodules = []
	filehandle = open(file)
	while 1:
		line = filehandle.readline()
		if not line:
			break
		
		splittedline = line.split(':')
		section = splittedline[0]
		modules = splittedline[1]
		modules = retrim(modules)
		modules = re.sub("\n","",modules)
		splittedmodules = modules.split(' ')
		for module in splittedmodules:
			if module:
				if allmodules.count(module) == 0:
					allmodules.append(module)




	filehandle.close()
	
	return allmodules

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


		

def displaySummary(xorg, kernelmodules, mac, configserver, interface):

	print
	log_begin_msg("My Configuration Server is: "+configserver, True, SUCCESS)
	log_begin_msg("My Network Interface is: "+interface+"("+mac+")", True, SUCCESS)
	log_begin_msg("Keyboard: "+xorg["gotoXKbLayout"]+" "+xorg["gotoXKbModel"]+" "+xorg["gotoXKbVariant"], True, SUCCESS)
	log_begin_msg("Mouse: "+xorg["gotoXMouseType"]+" "+xorg["gotoXMouseport"], True, SUCCESS)
	log_begin_msg("Graphics-Settings: "+" "+xorg["gotoXDriver"]+" "+xorg["gotoXColordepth"]+" "+xorg["gotoXResolution"]+" "+xorg["gotoXHsync"]+" "+xorg["gotoXVsync"], True, SUCCESS)
	log_begin_msg("Kernel Modules detected: ", False)
	for mod in kernelmodules:
		print mod,
	print SUCCESS

	raw_input("\n\nPress the ENTER to write back changes to ldap.")

	syslog.openlog(syslogident,0, syslog.LOG_LOCAL5)
	syslog.syslog(mac+" HWD_FINISHED.")

def getNic(file):

        filehandle = open(file)
	netmodule = ""

        while 1:
                line = filehandle.readline()
                if not line:
                        break

		netmodule = line

	filehandle.close()

	netmodules = netmodule.split("/")	
	for mod in netmodules:
		if mod.count(".ko") > 0:
			netmodule = mod
	netmodule=re.sub(".ko","",netmodule)


        attrs = {}

        attrs['ghNetNic'] = netmodule


	return attrs

def getLdapBase():

        ldapbase = retrim(open('/etc/opendwarf/ldap.base','r').readlines()[0])

        return ldapbase

def main():

	try:

		syslog.syslog(syslogprefix+'syslogident script got woken up.')
		log_begin_msg("launching "+syslogident, True)

		detectedKernelModulesFile = "/tmp/hwd.txt"	
		xorgconfFile ="/etc/X11/xorg.conf"
		secondxorgconfFile ="/xorg.conf.new"
	
		configserver = getConfigserverIP()


		if not configserver:
			log_error_msg("searching configserver", False, FAILED)
			sys.exit(1)

	
		ldapuri = "ldap://"+configserver+":389"
		ldapbase = getLdapBase()
		ldapfilter = ""
		ldapwriteuser = "cn=gimli,"+ldapbase
		ldapwritepassword = "gimlisonfofgloin"
		ldapWantedDnAttributes=["gotoModules","gotoXResolution","gotoXDriver","gotoXColordepth", "gotoXHsync", "gotoXVsync", "gotoXMouseType", "gotoXMouseport", "gotoXKbLayout", "gotoXKbModel", "gotoXKbVariant", "ghNetNic"]
		currentKernelModulesAttrsNames = ["gotoModules"]
		currentXorgAttrsNames = ["gotoXResolution","gotoXDriver","gotoXColordepth", "gotoXHsync", "gotoXVsync", "gotoXMouseType", "gotoXMouseport", "gotoXKbLayout", "gotoXKbModel", "gotoXKbVariant"]
		currentNicAttrsNames = ["ghNetNic"]

		retrievedDnAttributes = {}
		
		interface="eth0"
		myMac = getMyMac(interface)
		#myMac = "00:0C:29:9A:BA:86"
		myLdapfilter="(macAddress="+str(myMac)+")"	

	
		myDN, retrievedAttriubutes = getLdapDn(ldapuri, ldapbase, myLdapfilter, ldapWantedDnAttributes)

		currentKernelModulesAttrs = {}
		for kernelmoduleattribute in currentKernelModulesAttrsNames:
			for entry in retrievedAttriubutes.keys():
				if entry == kernelmoduleattribute:
					currentKernelModulesAttrs[kernelmoduleattribute]=retrievedAttriubutes[entry]
		currentNicAttrs = {}
		for nicattribute in currentNicAttrsNames:
			for entry in retrievedAttriubutes.keys():
				if entry == nicattribute:
					currentKernelModulesAttrs[nicattribute]=retrievedAttriubutes[entry]
	
		currentXorgAttrs = {}
		for xorgattribute in currentXorgAttrsNames:
			for entry in retrievedAttriubutes.keys():
				if entry == xorgattribute:
					currentXorgAttrs[xorgattribute]=retrievedAttriubutes[entry]

		
	


		if myDN == "empty":
			print "haven't found me ("+myMac+") in ldap directory"
			sys.exit(1)

		myXorgAttrs = parseXorgConfigFile(xorgconfFile)
		myXorgAttrs2 = parseXorgConfigFile(secondxorgconfFile)
		try:
		 if myXorgAttrs2["gotoXDriver"] != "vesa":
			myXorgAttrs["gotoXDriver"] = myXorgAttrs2["gotoXDriver"]
		except KeyError:
			pass

                myXorgAttrs["gotoXMouseport"] = "/dev/psaux"
                myXorgAttrs["gotoXMouseType"] = "ImPS/2"

		
		myKernelModules = parseDetectedKernelModulesFile(detectedKernelModulesFile)
		myNicAttrs = getNic("/etc/nic")
		

		displaySummary(myXorgAttrs, myKernelModules, myMac, configserver, interface)


		addMyKernelModules(ldapuri, ldapbase, ldapwriteuser, ldapwritepassword, myDN, myKernelModules, currentKernelModulesAttrs)
		addXorgAttributes(ldapuri, ldapbase, ldapwriteuser, ldapwritepassword, myDN, myXorgAttrs, currentXorgAttrs)
		addNicAttributes(ldapuri, ldapbase, ldapwriteuser, ldapwritepassword, myDN, myNicAttrs, currentNicAttrs)


		raw_input("\n\nPlease move your new client to the OU you want and press ENTER for reboot.")


		retrievedAttriubutes = {}
		ldapWantedDnAttributes=["member"]
		myLdapfilter="(description=timeserver_settings)"
                timeserverDN, retrievedTimeserverAttriubutes = getLdapDn(ldapuri, ldapbase, myLdapfilter, ldapWantedDnAttributes)

		myDNattrrs = {}
        	myDNattrrs['member'] = [myDN]

	except KeyboardInterrupt:
		print "Ctrl+C recognized."
		sys.exit(1)

if __name__=='__main__': main()

