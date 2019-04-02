FireProx
==================
- [Overview](#overview)
	- [Benefits](#benefits)
	- [Disclaimers](#disclaimers)
- [Maintainer](#maintainer)
- [Basic Usage](#basic-usage)
- [Installation](#installation)
- [Screenshots](#screenshots)
- [Contributing](#contributing)

## Overview ##
Being able to hide or continually rotate the source IP address when making web calls can be difficult or expensive. A number of tools have existed for some time but they were either limited with the number of IP addresses, were expensive, or required deployment of lots of VPS's. FireProx leverages the AWS API Gateway to create pass-through proxies that rotate the source IP address with every request! Use FireProx to create a proxy URL that points to a destination server and then make web requests to the proxy URL which returns the destination server response!

**Brought to you by:**

![Black Hills Information Security](https://www.blackhillsinfosec.com/wp-content/uploads/2016/03/BHIS-logo-L-300x300.png "Black Hills Information Security")

## Maintainer
- Follow me on Twitter for more tips, tricks, and tools (or just to say hi)! ([Mike Felch - @ustayready](https://twitter.com/ustayready)) 

### Benefits ##

 * Rotates IP address with every request
 * Configure separate regions
 * All HTTP methods supported
 * All parameters and URI's are passed through
 * Create, delete, list, or update proxies
 
### Disclaimers ##
 * Source IP address is passed to the destination in the X-Forwarded-For header by AWS
   * ($100 to the first person to figure out how to strip it in the AWS config before it reaches the destination LOL!)
 * I am not responsible if you don't abide by the robots.txt :)
 * CloudFlare seems to sometimes detect X-Forwarded-For when blocking scrapers
 
## Basic Usage ##
### Requires AWS access key and secret access key or aws cli configured
usage: **fire.py** [-h] [--access_key ACCESS_KEY]
               [--secret_access_key SECRET_ACCESS_KEY] [--region REGION]
               [--command COMMAND] [--api_id API_ID] [--url URL]

FireProx API Gateway Manager
```
optional arguments:
  -h, --help            show this help message and exit
  --access_key ACCESS_KEY
                        AWS Access Key
  --secret_access_key SECRET_ACCESS_KEY
                        AWS Secret Access Key
  --region REGION       AWS Region
  --command COMMAND     Commands: list, create, delete, update
  --api_id API_ID       API ID
  --url URL             URL end-point
```

* Examples
	* examples/google.py: Use a FireProx proxy to scrape Google search.
	* examples/bing.py: Use a FireProx proxy to scrape Bing search.
         
## Installation ##
You can install and run with the following command:

```bash
$ git clone https://github.com/ustayready/fireprox
$ cd fireprox
~/fireprox$ virtualenv -p python3 .
~/fireprox$ source bin/activate
(fireprox) ~/fireprox$ pip install -r requirements.txt
(fireprox) ~/fireprox$ python fire.py
```

Note that Python 3 is required.

## Screenshots
![Usage](https://github.com/ustayready/fireprox/blob/master/screenshots/usage.png "usage")
![List](https://github.com/ustayready/fireprox/blob/master/screenshots/list.png "list")
![Create](https://github.com/ustayready/fireprox/blob/master/screenshots/create.png "create")
![Delete](https://github.com/ustayready/fireprox/blob/master/screenshots/delete.png "delete")
![Demo](https://github.com/ustayready/fireprox/blob/master/screenshots/demo.png "demo")

## Contributing

1. Create an issue to discuss your idea
2. Fork FireProx (https://github.com/ustayready/fireprox/fork)
3. Create your feature branch (`git checkout -b my-new-feature`)
4. Commit your changes (`git commit -am 'Add some feature'`)
5. Push to the branch (`git push origin my-new-feature`)
6. Create a new Pull Request

**Bug reports, feature requests and patches are welcome.**
