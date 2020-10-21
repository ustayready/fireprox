# Before using this script, use fireprox to create a proxy to an IP reporting api.
# Warning: some IP reporting apis take X-Forwarded-For and display that instead
# of the actual IP the request came from. I've found that https://api.my-ip.io/ip
# IGNORES the X-Forwarded-For header, allowing you to see the AWS IP that made
# the request

# Once the fireprox proxy is made to a site like https://api.my-ip.io/ip run:
# python testip.py <fireprox_url>
# Each execution should show a new IP

import requests
import sys

url = sys.argv[1]
print(requests.get(url).text)
