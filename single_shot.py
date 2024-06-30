#!/usr/local/bin/python3.9
# 
# Poll the local API for my ENPHASE Envoy to get individual inverter status
# Requires get_tokey.py which contains my username and password...
#   To modify this for your temporary, private use, simply return your token from get_token() instead of dynamically updating it
# 

import json
import http.client
import ssl
import platform
import pprint
import datetime
import get_token
import os.path

if platform.system() == "Windows":
    # used to test this code using VS Code on Windows
    BASE_DIR='w:'
else:
    # normally runs on my synology platform
    BASE_DIR='/volume1/web'

URL_BASE     ="https://ikassman.synology.me/invdata/"  # publicly visible access to my data.  Must be same site as my web-pages that use this data
DATA_DIR     =BASE_DIR+'/invdata/'                     # where I put the inverter data, manifest, and access keys
MANIFEST_FILE=DATA_DIR+"sm_manifest.json"              # manifest name
TOKEN        =DATA_DIR+'.token/local_api_token.json'   # access token
LOCAL_API_IP ="192.168.0.213"                          # local IP address of my ENVOY

TEST_ONLY=False                                        # if True, print only, don't update files
DATE_FMT="%Y-%m-%d"                                    # used to create filenames for each day's data

#
# get the access token for reading from the envoy local API
def get_token():
    try:
        # get the prior data
        with open(TOKEN,'r') as f:
            token=json.load(f)
    except:
        print("missing token file")
        exit()
    #
    # Can't figure out a way to get the token expiration date.  Assume 365 days.  Use 200 days just to be safe
    #
    if  datetime.datetime.fromtimestamp(token['date'])+datetime.timedelta(days=200) < datetime.datetime.today():
        # need to refresh the token
        print("need to refresh token")
        access_token = get_token.get_new_token()
    else:
        access_token = token['access_token']
    
    return access_token

#
# read the prior data that we're going to append to
def get_prior_data(file):
    t_inverters={}
    try:
        # get the prior data
        with open(file,'r') as f:
            t_inverters=json.load(f)
    except:
        print("initial run")

    return t_inverters
    
#
# Translate serial number to inveter name.  In my case the name indicates the location on the roof
def get_name(sn):
    name_table = {  202326182843:"West-2.4",
                    202326189397:"West-2.3",
                    202326189803:"West-2.2",
                    202326179873:"West-2.1",
                    202326181290:"West-1.3",
                    202326097201:"West-1.2",
                    202326101609:"West-1.1",
                    202326179878:"East-5",
                    202326199306:"East-4",
                    202326101116:"East-3",
                    202326199773:"East-2",
                    202326195868:"East-1"
    }
    if sn in name_table:
        name = name_table[sn]
    else:
        name = sn

    return name

#
# Add the current sample 'invData' to the prior list 'inverters'
# return True if 'invData' included new information, False if it was already in 'inverters'
def add_data(inverters,invData):
    bChange=False
    for elem in invData:
        sn = int(elem['serialNumber'])
        lrd = elem['lastReportDate']
        name = get_name(sn)
        if name not in inverters:
            inverters[name] = {}
            inverters[name]['sn']=sn
            inverters[name]['data']=[]

        if lrd != inverters[name]['data'][-1]['epoch']:
           inverters[name]['data'].append({'epoch':lrd, 'watts':elem['lastReportWatts']})
           bChange=True
    return bChange

#
# read the individual inverter status from my ENVOY's local API
# returns the data read
def readEnvoy(sQuery, print_json=False, print_response=False):
    access_token = get_token()
    payload = ''
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer '+access_token
    }
    conn = http.client.HTTPSConnection(LOCAL_API_IP,context = ssl._create_unverified_context())
    conn.request("GET",sQuery, payload, headers)
    res = conn.getresponse()
    t = res.read()
    if print_response: print(t)
    d = json.loads(t)
    if print_json:     print(d)
    return d

#
# Add an entry for this day to the manifest
def add_to_manifest(dt):
    # read the current manifest
    try:
        with open(MANIFEST_FILE,'r') as f:
            by_year=json.load(f)
    except:
        print("no prior data")
        by_year={}
    
    year_name  = str(dt.year)
    month_name = dt.strftime("%B")
    day_name   = str(dt.day)
    url_name   = URL_BASE+dt.strftime(DATE_FMT)+'.json'
    if year_name not in by_year:
        by_year[year_name]={}
    if month_name not in by_year[year_name]:
        by_year[year_name][month_name]={}
    if day_name not in by_year[year_name][month_name]:
        by_year[year_name][month_name][day_name] = url_name
        pretty_json_str = pprint.pformat(by_year, compact=True).replace("'",'"')
        if TEST_ONLY:
            print("manifest: %s"%(MANIFEST_FILE))
            print(pretty_json_str)
        else:
            with open(MANIFEST_FILE,'w') as f:
                f.write(pretty_json_str)

#
# Main code
if __name__ == "__main__":
    
    # read the detailed inverter status
    snapshot = readEnvoy('/api/v1/production/inverters')

    # Just in case some inverters are on one side of midnight, and some on the other
    # always use the date of the earliest day.
    # Should never happen as the inverters are not reporting during the night.
    smallest = min(snapshot, key=lambda x: x['lastReportDate'])
    earliestDate = smallest['lastReportDate']
    
    #
    # get the prior readings for this day
    dt = datetime.datetime.fromtimestamp(earliestDate)
    fileName = DATA_DIR+dt.strftime(DATE_FMT)+'.json'
    if os.path.isfile(fileName):
        # read the prior data.  We'll just add to it
        inverters = get_prior_data(fileName)
    else:
        # this is the first entry for the day
        # we'll start with an empty dictionary
        inverters = {}
        # since it's the first time this day was seen, add it to the manifest
        add_to_manifest(dt)

        
    # Add the new data to what we read in.
    # If there was a change in data, write the updated data to the file
    # We're over sampling, so just trying to save some file writes.
    if (add_data(inverters,snapshot)):
        pretty_json_str = pprint.pformat(inverters, compact=True).replace("'",'"')
        if TEST_ONLY:
            print(pretty_json_str)
        else:
            with open(fileName,'w') as f:
                f.write(pretty_json_str)
