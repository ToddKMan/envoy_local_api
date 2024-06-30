#!/usr/local/bin/python3.9

# Get the envoy token for the local API

import json
import platform

from urllib.parse import urlencode
from urllib.request import Request, urlopen


#
# private data file contains username, password, and envoy serial number in json format, eg:
#  {
#    "user":         "someone@gmail.com",
#    "password":     "abc123",
#     "envoy_serial":"202332112345"
#  }
#
if platform.system() == "Windows":
    # used to test this code using VS Code on Windows
    PRIVATE_DATA_FILE="h:/Documents/Enphase/private.json"
else:
    # normally runs on my synology platform
    PRIVATE_DATA_FILE="/volume1/homes/Dad/Documents/Enphase/private.json"

#
# get a new token from enphase and return it to the caller as a string
def get_new_token():
    # get the prior data
    with open(PRIVATE_DATA_FILE,'r') as f:
        private_data=json.load(f)

    user        =private_data['user']
    password    =private_data['password']
    envoy_serial=private_data['envoy_serial']
    print(user, password, envoy_serial)
    
    data = {'user[email]': user, 'user[password]': password}

    request = Request('https://enlighten.enphaseenergy.com/login/login.json?',urlencode(data).encode())
    with urlopen(request) as response:
        response_data = json.loads(response.read().decode())

    
    data = {'session_id': response_data['session_id'], 'serial_num': envoy_serial, 'username':user}
    data_bytes = bytes(json.dumps(data), encoding='utf8')
    request = Request('https://entrez.enphaseenergy.com/tokens',data=data_bytes,headers={'Content-Type': 'application/json'})
    with urlopen(request) as response:
        token = response.read().decode()
    
    return token

if __name__ == "__main__":
    print(get_new_token())