#!/usr/bin/python2.5

"""
This script will scrape the most recent versions of each Future
Business section and pages from the calendar in the future.  Pages are
only written if they are different from the most recent version.  The
output is to the PAGE_STORE directory defined in future_business.py.
"""

from future_business import *

import os
import errno
import re
import sys
import glob

import datetime
import dateutil.parser

import time

# Trying out httplib2. This hasn't reached 1.0 yet, but I think it's worth
# giving it a go to avoid having to think about caching, downloading headers,
# etags, etc. manually.

import httplib2

# Location of the cache directory for httplib2
cache_directory = '.cache'

# This will cause a directory for httplib2 to use for its
# cache to be created if it doesn't already exist.
http_fetcher = httplib2.Http(cache_directory)

timestamp_re = re.compile('^(.*)-\d{8}T\d{6}.html$')

def create_and_enter_directory(directory_name):
    """Change the current working directory to that with name
    'directory_name', creating it if it doesn't already exist."""

    try:
        os.mkdir(directory_name)
    except OSError, e:
        # Ignore the error if it already exists
        if e.errno != errno.EEXIST:
            raise
    os.chdir(directory_name)

def write_if_changed(directory_name,
                     filename,
                     content):
    # Store the current working directory so we can go back at the end.
    original_directory = os.getcwd()

    create_and_enter_directory(directory_name)

    try:
        filename_match = timestamp_re.search(filename)
        if not filename_match:
            raise "Failed to match the filename '"+filename+"', expected to match: "+timestamp_re.pattern

        prefix = filename_match.group(1)
        earlier_files = matching_ordered(prefix+"-",".html")

        if len(earlier_files) > 0:
            fp = open(earlier_files[-1])
            latest_file_content = fp.read()
            fp.close()
            if latest_file_content == content:
                # It's just the same as the last version, don't bother saving it...
                print "   Not writing "+filename+", the content is the same as "+earlier_files[-1]
                return False

        print "Writing a file with updated contents: "+filename

        # Otherwise we should just write the file:
        fp = open(filename, 'w')
        fp.write(content)
        fp.close()
        return True

    finally:
        # Return to the original directory
        os.chdir(original_directory)

tidy_class_re = '(class="[^"]+) today([^"]*")'
tidy_class_replacement = '\\1\\2'

tidy_class_start_re = '(class=")today '
tidy_class_start_replacement = '\\1'

tidy_class_just_re = 'class="today"'
tidy_class_just_replacement = 'class=""'

if __name__ == '__main__':

    d = start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=CALENDAR_DAYS)

    while True:
        if d > end_date:
            break

        if d.isoweekday() in (6,7):
            d += datetime.timedelta(days=1)
            continue

        for section in CALENDAR_SECTIONS:
            formatted_date = d.strftime(CALENDAR_URL_DATE_FORMAT)
            calendar_url_format = CALENDAR_SECTIONS[section]
            url = calendar_url_format % (formatted_date,)
            response, content = http_fetcher.request(url)
            content = re.sub(tidy_class_re,tidy_class_replacement,content)
            content = re.sub(tidy_class_start_re,tidy_class_start_replacement,content)
            content = re.sub(tidy_class_just_re,tidy_class_just_replacement,content)
            time.sleep(4)
            response_timestamp = dateutil.parser.parse(response['date'])
            page_filename = CALENDAR_PAGE_FILENAME_FORMAT % (section,d,response_timestamp.strftime(FILENAME_DATE_FORMAT))
            updated = write_if_changed(PAGE_STORE,
                                       page_filename,
                                       content)
        d += datetime.timedelta(days=1)

    for part in FUTURE_BUSINESS_PARTS:
        url = FUTURE_BUSINESS_TEMPLATE_LOCATION % (part,)

        # Fetch the current version of Future Business for a particular part:
        response, content = http_fetcher.request(url)
        content = re.sub(tidy_class_re,tidy_class_replacement,content)

        # Example response:
        #   {'status': '200',
        #    'content-length': '94447',
        #    'content-location': 'http://www.publications.parliament.uk/pa/cm/cmfbusi/a01.htm',
        #    'vary': 'Accept-Encoding',
        #    'server': 'Netscape-Enterprise/6.0',
        #    'connection': 'keep-alive',
        #    'date': 'Tue, 18 Aug 2009 23:38:28 GMT',
        #    'content-type': 'text/html'}

        if re.search('^[45]',response['status']):
            print >> sys.stderr, "Error %s fetching %s" % (response['status'],url)
            continue

        response_timestamp = dateutil.parser.parse(response['date'])

        page_filename = PAGE_FILENAME_FORMAT % (part,response_timestamp.strftime(FILENAME_DATE_FORMAT))

        # Check if we need to store a copy of the page and do so if we do.
        updated = write_if_changed(PAGE_STORE,
                                   page_filename,
                                   content)