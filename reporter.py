#!/usr/bin/env python
#
#The MIT License (MIT)
#
# Copyright (c) 2015 Bit9 + Carbon Black
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# -----------------------------------------------------------------------------
#  This script is designed to output Process, Binary or Alert queries into a
#  multitabbed Excel SpreadSheet.
#
#  It takes a configuration file in the format of:
#  [Tab Name]
#  Type = binary|process|alert
#  Fields = <query output fields to display per column>
#  Query = <the Carbon Black query you want to run>
#
#  Thew output is completely customizable based on the values in the config
#  file.  This script was mainly designed for IR teams on proactive engagements 
#  to provide a leave behind to customers.
#
#  created 2016-03-02 by James Darby jdarby@carbonblack.com
#
# ------------------------------------------------------------------------------
#  TODO:
#
# ------------------------------------------------------------------------------

import sys
import optparse
import cbapi
import ConfigParser
import os
from openpyxl import Workbook
from openpyxl.cell import get_column_letter, column_index_from_string

def build_cli_parser():
    parser = optparse.OptionParser(usage="%prog [options]", description="Perform a binary search")

    # for each supported output type, add an option
    #
    parser.add_option("-a", "--apitoken", action="store", default=None, dest="token",
                      help="API Token for Carbon Black server")
    parser.add_option("-b", "--blank-tabs", action="store_false", default=True, dest="blanktabs",
                      help="Display blank tabs in Excel if the query returns no results.")
    parser.add_option("-c", "--cburl", action="store", default=None, dest="url",
                      help="CB server's URL.  e.g., http://127.0.0.1 ")
    parser.add_option("-f", "--configfile", action="store", default=None, dest="configfile",
                      help="This is the configuratiom file")
    parser.add_option("-n", "--no-ssl-verify", action="store_false", default=True, dest="ssl_verify",
                      help="Do not verify server SSL certificate.")
    parser.add_option("-o", "--outfile", action="store", default=None, dest="outfile",
                      help="This is the name of the spreadsheet that we'll create")
    parser.add_option("-p", "--process-link", action="store_false", default=True, dest="processlink",
                      help="Display blank tabs in Excel if the query returns no results.")
    parser.add_option("-s", "--page-size", action="store", default=None, dest="page_size",
                      help="This allows you to change the default pagination (3000) to grab more data.")
    parser.add_option("-v", "--verbose", action="store_false", default=True, dest="verbose",
                      help="Print the progession through the queries.")
    return parser

def main(argv):
    parser = build_cli_parser()
    opts, args = parser.parse_args(argv)
    if not opts.url or not opts.token or opts.configfile is None or opts.outfile is None:
        print "Missing required param; run with --help for usage"
        sys.exit(-1)

    # build a cbapi object
    #
    cb = cbapi.CbApi(opts.url, token=opts.token, ssl_verify=opts.ssl_verify)

    config = ConfigParser.ConfigParser()

    # build the Excel workbook
    #
    wb = Workbook()

    # read the config file in
    #
    config.readfp(open(opts.configfile))

    # loop through the config file to pull each query
    #
    for each_section in config.sections():

        if config.get(each_section, "type") == 'binary':
            try:
                seedquery = cb.binary_search(config.get(each_section, "query"),0,1)
                total_results = seedquery['total_results']
                if total_results == 0 and opts.blanktabs:
                    continue
            except:
                e = sys.exc_info()[0]
                print e
                continue
        elif config.get(each_section, "type") == 'process':
            try:
                seedquery = cb.process_search(config.get(each_section, "query"),0,1)
                total_results = seedquery['total_results']
                if total_results == 0 and opts.blanktabs:
                    continue
            except:
                e = sys.exc_info()[0]
                print e
                continue
        elif config.get(each_section, "type") == 'alert':
            try:
                seedquery = cb.alert_search(config.get(each_section, "query"),0,1)
                total_results = seedquery['total_results']
                if total_results == 0 and opts.blanktabs:
                    continue
            except:
                e = sys.exc_info()[0]
                print e
                continue
        # print the current query if in verbose mode
        #
        if not opts.verbose:
            print 'Working on query:',config.get(each_section, "query")

        # prune the tab name to 31 for excel
        #
        tabname = each_section[:31]

        # create a unique tab name
        #
        wb.create_sheet(tabname)

        # grab the active worksheet
        #
        ws = wb.get_sheet_by_name(tabname)

        # Query for the data
        #
        myheader = config.get(each_section, "fields").split(",")

        if not opts.processlink:
            myheader.insert(0,"Link")

        # print the header for each sheet
        #
        col = 0
        for this in myheader:
            col += 1
            ws.cell(row=1, column=col).value = this
        row = 1
        start = 0
        if opts.page_size:
            pagesize = int(opts.page_size)
        else:
            pagesize = 3000
        while True:
            # for each result 
            if config.get(each_section, "type") == 'binary':
                searchquery = cb.binary_search(config.get(each_section, "query"),start,start + pagesize)
            elif config.get(each_section, "type") == 'process':
                searchquery = cb.process_search(config.get(each_section, "query"),start,start + pagesize)
            elif config.get(each_section, "type") == 'alert':
                searchquery = cb.alert_search(config.get(each_section, "query"),start,start + pagesize)
            if len(searchquery['results']) == 0: break
            for tags in searchquery['results']:
                row += 1
                col = 0
                for item in myheader:
                    col += 1
                    if item == "Link":
                        proclink = opts.url
                        if config.get(each_section, "Type") == "process":
                            proclink += '/#analyze/'
                            proclink += unicode(tags.get("unique_id")[:36])
                            proclink += '/'
                            proclink += unicode(tags.get("segment_id"))
                        elif config.get(each_section, "Type") == "alert":
                            proclink += '/#analyze/'
                            proclink += unicode(tags.get("process_id"))
                            proclink += '/'
                            proclink += unicode(tags.get("segment_id"))
                        elif config.get(each_section, "Type") == "binary":
                            proclink += '/#/binary/'
                            proclink += unicode(tags.get("md5"))
                        ws.cell(row=row, column=col).hyperlink = proclink
                    else:
                        ws.cell(row=row, column=col).value = unicode(tags.get(item, '<UNKNOWN>'))
            start = start + int(pagesize)

    # save the wookbook
    #
    wb.remove_sheet(wb.get_sheet_by_name('Sheet'))
    wb.save(opts.outfile)    

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
