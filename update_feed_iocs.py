#!/usr/bin/python

#################################################################################
##  Indicator Deprecator Script
##        By Ben Tedesco
##  
## This script will rename IOCs in the Cb Response Feeds SOLR Core to allow one 
## to selectively "disable" benign/false positive IOCs without needing to disable
## an entire IOC report (especially those that contain multiple indicators). This
## is accomplished by prefixing selected IOCs with a text string to prevent a 
## match, the default prefix is "WHITELISTED."
##
## It is suggested that this script be run on a cron job to regularly ensure the
## Solr Core is "cleaned"
##
## NOTE: This script references a text file "bad_iocs.txt" that contains the list
## of iocs that need to "disabled". This file should only have 1 indicator per line
##
## ------------------------------------------------------------------------------
##  Release History
##  05-31-2017  - Initial Release. This does not have error checking built in to
##		validate the "bad_iocs.txt" file. This could be added later 
##
##
##
##
##
##################################################################################

import os
import requests
import re

#######################  SELECT 
##     curl 'http://localhost:8080/solr/cbfeeds/select?q=domain%3Amicrosofthomes..com&fl=iocs_json&wt=json&indent=true'
################################

bad_ioc_file = "bad_iocs.txt"

with open(bad_ioc_file) as f:
    content = f.readlines()
# you may also want to remove whitespace characters like `\n` at the end of each line
content = [x.strip() for x in content] 
print "Removing IOCS:"
print("\n".join(content))
print ""
print "------------------------------"

for bad_ioc in content:

	## bad_ioc = "login-one.com"
	bad_ioc_doubledot = bad_ioc.replace(".", "..")
	## print "bad_ioc_doubledot " + bad_ioc_doubledot

	solr_select_request = "http://localhost:8080/solr/cbfeeds/select?q=domain%3A" + bad_ioc_doubledot + "&wt=json&indent=true"

	r = requests.get(solr_select_request)
	## print r.json()
	## print r.text

	# Get Full IOC Report
	m = re.search('(iocs_json.*)', r.text)
	iocs = "\"" + m.group(0)
	## print "iocs: " + iocs
	## iocs ==iocs: "iocs_json":"{\"dns\": [\"microsofthomes.com\"]}",

	# Replace IOC in report by prefixing it with "WHITELISTED." and update query for SOLR 'SET' command
	new_ioc_CONST = "WHITELISTED."
	iocs = iocs.replace(bad_ioc, new_ioc_CONST + bad_ioc)
	iocs = iocs.replace("_json\":", "_json\":{\"set\":")
	iocs = iocs[0:len(iocs)-1]
	## print "CLEANED iocs: " + iocs

	# Find update_time paramater
	m = re.search('(update_time.*)', r.text)
	updated_time = "\"" + m.group(0)
	## print "updated_time: " + updated_time
	## update_time=="update_time":1401326996,

	# Increment update_time paramater
	updated_time = updated_time[14:len(updated_time)-1]
	## print "NEW updated_time: " + updated_time
	updated_time = str(int(updated_time) + 1)
	## print "NEW updated_time: " + updated_time

	# Findi & parse the IOC Report's  'unique_id' in the SOLR document
	m = re.search('(unique_id.*)', r.text)
	uni_id = "\"" + m.group(0)
	## print "uni_id: " + uni_id
	## uni_id: "unique_id":"12:176459",
	uni_id = uni_id[13:len(uni_id)-2]
	## print "NEW uni_id: " + uni_id


	############################  REPLACE
	##    curl 'http://localhost:8080/solr/cbfeeds/update?commit=true' -H 'Content-type:application/json' -d '[{"update_time":{"set":1401326993},"unique_id":"12:79867","iocs_json":{"set":"{\"dns\": [\"masalavideos.no-ip.bizzzzzzz\"]}"}}]'
	######################################

	solr_update_request = "\'http://localhost:8080/solr/cbfeeds/update?commit=true\' -H \'Content-type:application/json\' -d \'[{\"update_time\":{\"set\":" + updated_time + "},\"unique_id\":\"" + uni_id + "\"," + iocs + "}}]\'"

	# run the SOLR update query
	## print solr_update_request

	os.system("curl " + solr_update_request)

	print "Indicator " + bad_ioc + " has been replaced with " + new_ioc_CONST + bad_ioc
	print "\n"

	# Verify the old IOC doesn't exist
	## r = requests.get(solr_select_request)
	## print r.json()
	## print r.text
	## print ""

