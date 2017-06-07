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
##  06-06-2017  - Added support for IPv4 & MD5 IOCs, misc formatting for IOCs, 
##		Error Handling, added support for IOCs in multiple feeds, renamed to script
##    "feed_ioc_cleaner.py".
##
##
##
##
##
##################################################################################

import os
import requests
import re
import socket, struct

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
	ioc_type=""
	formatted_ioc=""

        ## Try to see if this is an MD5 IOC
        validHash = re.finditer(r'(?=(\b[A-Fa-f0-9]{32}\b))', bad_ioc)
        result = [match.group(1) for match in validHash]

        if result:
                ioc_type = "md5"
                formatted_ioc = bad_ioc
                #print "Valid MD5./nFormatted IOC: " + formatted_ioc
        else:
                try:
                        ## See if this is an IPv4 IOC
                        packedIP = socket.inet_aton(bad_ioc)
                        formatted_ioc = str(struct.unpack(">i", packedIP)[0])
			
			# since using signed int, need to prefix with '\' in case '-' is 1st char
			formatted_ioc = "\\" + formatted_ioc
                        ioc_type = "ipaddr"
                        #print "Valid IP./nFormatted IOC: " + formatted_ioc
                except:

                        ioc_type = "domain"
                        # double '.' to search db for domain
                        formatted_ioc = bad_ioc.replace(".", "..")
                        #print "Must Be a Domain./nFormatted IOC: " + formatted_ioc

        ## print "Original IOC: " + bad_ioc + "\nIOC Type: " + ioc_type + "\nFormatted IOC: " + formatted_ioc + "\n------------------------------"

	#######################  SELECT IOC from Feeds DB ##############################
	##     curl 'http://localhost:8080/solr/cbfeeds/select?q=domain%3Amicrosofthomes..com&fl=iocs_json&wt=json&indent=true'
	################################################################################

	solr_select_request = "http://localhost:8080/solr/cbfeeds/select?q=" + ioc_type + "%3A" + formatted_ioc + "&wt=json&indent=true"

	r = requests.get(solr_select_request)
	## print r.json()
	## print r.text

        # Get Full IOC Report
        p = re.compile('(iocs_json.*)')
        iterator = p.finditer(r.text)
	count = 0

        for match in iterator:
                ## print "\n\n\n\n\n\n\n--------------------------------------\nHERE IS THE MATCH for: " + bad_ioc + "\n" + match.group(1)

		try:
			# Determine if the ioc exists
			iocs = "\"" + match.group(1)
			## print "iocs: " + iocs

			# Replace domain IOC in report by prefixing it with "WHITELISTED."
			# NOTE: MD5 & IPv4 IOCS must be removed to ensure proper formatting
			if ioc_type == "domain":
				domain_ioc_CONST = "WHITELISTED."
				iocs = iocs.replace(bad_ioc, domain_ioc_CONST + bad_ioc)
			else:
			# Remove bad MD5 or IPv4
				iocs = iocs.replace(bad_ioc, "")

			# update query for SOLR 'SET' command
			iocs = iocs.replace("_json\":", "_json\":{\"set\":")

			# remove trailing ','
			iocs = iocs[0:len(iocs)-1]

			# remove \"\",  - case for when there are multiple elements and this is not the last
			iocs = iocs.replace("\\\"\\\", ", "" )

			# remove , \"\" - case for when there are multiple elements and this is the last element
			iocs = iocs.replace(", \\\"\\\"", "" )

			# remove \"\" - case for when this is the only or the last element
			iocs = iocs.replace("\\\"\\\"", "" )
			## print "CLEANED iocs:\n" + iocs
			
			# Find update_time paramater
			m = re.findall('(update_time.*)', r.text)
			updated_time = "\"" + m[count]
			# Trim updated time
			updated_time = updated_time[14:len(updated_time)-1]
			# Increment update_time paramater
			updated_time = str(int(updated_time) + 1)
			## print "NEW updated_time: " + updated_time

			# Findi & parse'unique_id' in IOC Report SOLR document
			m = re.findall('(unique_id.*)', r.text)
			uni_id = "\"" + m[count]

			# Trim uni_id
			uni_id = uni_id[13:len(uni_id)-2]
			## print "NEW uni_id: " + uni_id

			############################  REPLACE IOC in Feeds DB ##############################
			##    curl 'http://localhost:8080/solr/cbfeeds/update?commit=true' -H 'Content-type:application/json' -d '[{"update_time":{"set":1401326993},"unique_id":"12:79867","iocs_json":{"set":"{\"dns\": [\"WHITELISTED.masalavideos.no-ip.biz\"]}"}}]'
			######################################

			solr_update_request = "\'http://localhost:8080/solr/cbfeeds/update?commit=true\' -H \'Content-type:application/json\' -d \'[{\"update_time\":{\"set\":" + updated_time + "},\"unique_id\":\"" + uni_id + "\"," + iocs + "}}]\'"
			## print "solr_update_request:\n" + solr_update_request

			## Debug if statement to bypass curl update of solr db
			## if 1 != 1:
			## raw_input('!!!!!!!!!!To REMOVE IOC, Press enter to continue!!!!!!!!!!!!!')

			# run the SOLR update query
			os.system("curl " + solr_update_request)

			print "Indicator " + bad_ioc + " has been cleaned.\n\n\n\n"
		except: 
			print "ERROR removing ioc: " + bad_ioc
		
		#increment for update_time & unique_id
		count = count + 1
		## Debug pause:
		## raw_input('NEXT MATCH IN ITERATOR Press enter to continue: ')

	## Debug Pause
	## raw_input('NEXT IOC Press enter to continue: ')
