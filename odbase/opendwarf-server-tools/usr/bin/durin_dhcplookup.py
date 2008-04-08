#!/usr/bin/env python
# Copyright (C) 2008    Stefan Nistelberger (scuq@abyle.org)
#                       Peter Laback (peter@laback.com)
# durin_dhcplookup.py
# durin_dhcplookup - opendwarf dhcp/ldap lookup 
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# http://www.gnu.org/licenses/gpl.txt

import os
import sys
import time
import re
import ldap
import ldap.modlist as modlist
import syslog
import signal
from optparse import OptionParser
try:
	from xml.dom.minidom import *
        from xml import xpath
except ImportError, msg:
        print "xml parser import error, please install python xpath modules (python-xml)"
        sys.exit(1)

syslogprefix="durin_dhcplookup: "

def retrim(inputstr):

        inputstr = re.sub("^[^\w]+","",inputstr)
        inputstr = re.sub("[^\w]+$","",inputstr)

        return inputstr


def getLdapDn(ldapuri, ldapbase, ldapfilter, scope=ldap.SCOPE_SUBTREE, retrieve_attributes=None, timeout=0):


	try:
		l = ldap.initialize(ldapuri)
        	l.bind_s('', '')
        except ldap.LDAPError, error_message:
                syslog.syslog(syslogprefix+str(error_message))
		sys.exit(1)


        result_set = []

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
                        return dn

                for i in range(len(result_set)):
                        for entry in result_set[i]:
                                try:
                                        dn = entry[0]

                                except:
                                        pass

        except ldap.LDAPError, error_message:
		l.unbind_s()
		syslog.syslog(syslogprefix+str(error_message))

	l.unbind_s()
        return dn

def getLdapBase(gosaconffile):

	gosaxml = xml.dom.minidom.parse(gosaconffile)

	ldapbaseurl = xpath.Evaluate('/conf/main/location[@name="default"]/referral/@url' , gosaxml)
	ldapbaseurl = ldapbaseurl[0].value


        ldapbaseRegExp = 'dc=(.*?)$'
        ldapbaseSnipper = re.compile(ldapbaseRegExp, re.DOTALL)
        ldapbase = ldapbaseSnipper.search(ldapbaseurl)
        ldapbase = ldapbase.group(1)
	ldapbase = "dc="+ldapbase

        ldapuriRegExp = '^(.*?)dc='
        ldapuriSnipper = re.compile(ldapuriRegExp, re.DOTALL)
        ldapuri = ldapuriSnipper.search(ldapbaseurl)
        ldapuri = ldapuri.group(1)

	
	

	return ldapbase, ldapuri



def getLdapCredentials(gosaconffile):

	gosaxml = xml.dom.minidom.parse(gosaconffile)
	
	ldapwriteuser = xpath.Evaluate('/conf/main/location[@name="default"]/referral/@admin' , gosaxml)
	ldapwriteuser = ldapwriteuser[0].value
	ldapwritepwd = xpath.Evaluate('/conf/main/location[@name="default"]/referral/@password' , gosaxml)
	ldapwritepwd = ldapwritepwd[0].value


	return ldapwriteuser, ldapwritepwd



def createNewClientSubOUs(ldapuri, newClientsOuDn, gosaconffile):

     try:
	user, pw = getLdapCredentials(gosaconffile)
        l = ldap.initialize(ldapuri)
        l.simple_bind_s(user, pw)


	attrs = {}
	attrs['objectclass'] = ['top','organizationalUnit']
	attrs['ou'] = ["systems"]


	ldif = modlist.addModlist(attrs)
	l.add_s("ou=systems,"+newClientsOuDn,ldif)

     except ldap.LDAPError, error_message:
	syslog.syslog(syslogprefix+str(error_message))
	pass

	attrs = {}
	attrs['objectclass'] = ['top','organizationalUnit']
	attrs['ou'] = ["workstations"]

	ldif = modlist.addModlist(attrs)
	l.add_s("ou=workstations,ou=systems,"+newClientsOuDn,ldif)

	l.unbind_s() 

     except ldap.LDAPError, error_message:
	l.unbind_s()
	syslog.syslog(syslogprefix+str(error_message))

def createNewClient(ldapuri, ldapbase, newClientsOuDn, clientMac, gosaconffile):

	user, pw = getLdapCredentials(gosaconffile)
	l = ldap.initialize(ldapuri)
	l.simple_bind_s(user, pw)

	cn=clientMac.replace(":","")

	
	# example: cn=test123,ou=workstations,ou=systems,dc=thintenders,dc=local
	dn = "cn="+cn+",ou=workstations,ou=systems,"+newClientsOuDn
	syslog.syslog(syslogprefix+dn)

	attrs = {}

	attrs['objectclass'] = ['top','gotoWorkstation','GOhard', 'FAIobject']	
	attrs['cn'] = cn
	attrs['macAddress'] = clientMac

	ldif = modlist.addModlist(attrs)

	try:
		l.add_s(dn,ldif)	
	except ldap.LDAPError, error_message:
        	syslog.syslog(syslogprefix+str(error_message))
		createNewClientSubOUs(ldapuri, newClientsOuDn, gosaconffile)
		l.add_s(dn,ldif)	

	l.unbind_s()

def tail_lines(fd, linesback = 10):
    # Contributed to Python Cookbook by Ed Pascoe (2003)
    avgcharsperline = 75

    while 1:
        try:
            fd.seek(-1 * avgcharsperline * linesback, 2)
        except IOError:
            fd.seek(0)

        if fd.tell() == 0:
            atstart = 1
        else:
            atstart = 0

        lines = fd.read().split("\n")
        if (len(lines) > (linesback+1)) or atstart:
            break

        avgcharsperline=avgcharsperline * 1.3

    if len(lines) > linesback:
        start = len(lines) - linesback - 1
    else:
        start = 0

    return lines[start:len(lines)-1]

def lookupMac(line,ldapuri, ldapbase, ldapfilter, newClientsOuDn, gosaconffile):

	macaddress=retrim(line)
	macaddress=macaddress.upper()

	macldapresult = "empty"

        ldapfilter="(macAddress="+macaddress+")"
        macldapresult = getLdapDn(ldapuri, ldapbase, ldapfilter)

        if macldapresult != "empty":
        	syslog.syslog(syslogprefix+'client already known within gosa.')
        else:
                syslog.syslog(syslogprefix+"new client "+macaddress+" detected.")
                createNewClient (ldapuri, ldapbase, newClientsOuDn, macaddress, gosaconffile)
 
	

def main():

  parser = OptionParser()
  parser.add_option("-a", "--address", dest="macaddress", help="run durin_dhcpmon daemon in foreground mode.")

  (options, args) = parser.parse_args()



  if not options.macaddress:
	print "use -h for help"
	sys.exit(0)
  else:
	try:

		syslog.syslog(syslogprefix+'durin_dhcplookup woken up.')

		macbytes = options.macaddress.split(':')
		macaddress = ""
		cnt = 0	
		for byte in macbytes:
			cnt = cnt + 1
			if len(byte) == 1:
				macaddress=macaddress+"0"+byte
			else:
				macaddress=macaddress+byte
					
			if cnt != 6:
				macaddress=macaddress+":"
		

		gosaconffile = '/etc/gosa/gosa.conf-trunk'	
		ldapbase, ldapuri = getLdapBase(gosaconffile)
		ldapfilter = ""
		new_clients_ou_filter = "(description=new_clients_ou)" 	
		
	
		newClientsOuDn = getLdapDn(ldapuri, ldapbase, new_clients_ou_filter)
		if newClientsOuDn == "empty":
			newClientsOuDn = ldapbase

		lookupMac(macaddress,ldapuri, ldapbase, ldapfilter, newClientsOuDn, gosaconffile)
	


	


	except KeyboardInterrupt:
		print "Ctrl+C recognized."
		sys.exit(1)

if __name__=='__main__': main()

