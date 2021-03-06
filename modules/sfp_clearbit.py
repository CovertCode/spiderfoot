#-------------------------------------------------------------------------------
# Name:         sfp_clearbit
# Purpose:      Query clearbit.com using their API.
#
# Author:      Steve Micallef <steve@binarypool.com>
#
# Created:     20/03/2017
# Copyright:   (c) Steve Micallef
# Licence:     GPL
#-------------------------------------------------------------------------------

import json
import base64
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

class sfp_clearbit(SpiderFootPlugin):
    """Clearbit:Footprint,Investigate,Passive:Search Engines:apikey:Check for names, addresses, domains and more based on lookups of e-mail addresses on clearbit.com."""

    # Default options
    opts = {
        "api_key": ""
    }

    # Option descriptions
    optdescs = {
        "api_key": "Clearbit.com API key."
    }

    # Be sure to completely clear any class variables in setup()
    # or you run the risk of data persisting between scan runs.

    results = None
    errorState = False

    def setup(self, sfc, userOpts=dict()):
        self.sf = sfc
        self.results = self.tempStorage()
        self.errorState = False

        # Clear / reset any other class member variables here
        # or you risk them persisting between threads.

        for opt in list(userOpts.keys()):
            self.opts[opt] = userOpts[opt]

    # What events is this module interested in for input
    def watchedEvents(self):
        return [ "EMAILADDR" ]

    # What events this module produces
    def producedEvents(self):
        return [ "RAW_RIR_DATA", "PHONE_NUMBER", "PHYSICAL_ADDRESS",
                 "AFFILIATE_INTERNET_NAME", "EMAILADDR" ]

    def query(self, t):
        ret = None

        api_key = self.opts['api_key']
        if type(api_key) == str:
            api_key = api_key.encode('utf-8')
        url = "https://person.clearbit.com/v2/combined/find?email=" + t
        token = base64.b64encode(api_key + ':'.encode('utf-8'))
        headers = {
            'Accept': 'application/json',
            'Authorization': "Basic " + token.decode('utf-8')
        }

        res = self.sf.fetchUrl(url, timeout=self.opts['_fetchtimeout'],
            useragent="SpiderFoot", headers=headers)

        if res['code'] != "200":
            self.sf.error("Return code indicates no results or potential API key failure or exceeded limits.",
                       False)
            return None

        try:
            ret = json.loads(res['content'])
        except Exception as e:
            self.sf.error("Error processing JSON response from clearbit.io: " + \
                          str(e), False)
            return None

        return ret

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        if self.errorState:
            return None

        if self.opts['api_key'] == "":
            self.sf.error("You enabled sfp_clearbit but did not set an API key!", False)
            self.errorState = True
            return None

        self.sf.debug("Received event, " + eventName + ", from " + srcModuleName)

        # Don't look up stuff twice
        if eventData in self.results:
            self.sf.debug("Skipping " + eventData + " as already mapped.")
            return None
        else:
            self.results[eventData] = True

        data = self.query(eventData)
        if not data:
            return None

        try:
            # Get the name associated with the e-mail
            if "person" in data:
                name = data['person']['name']['fullName']
                evt = SpiderFootEvent("RAW_RIR_DATA", "Possible full name: " + name,
                                      self.__name__, event)
                self.notifyListeners(evt)
        except Exception:
            self.sf.debug("Unable to extract name from JSON.")
            pass

        # Get the location of the person, also indicating
        # the location of the employer.
        try:
            if "geo" in data:
                loc = ""

                if 'streetNumber' in data['geo']:
                    loc += data['geo']['streetNumber'] + ", "
                if 'streetName' in data['geo']:
                    loc += data['geo']['streetName'] + ", "
                if 'city' in data['geo']:
                    loc += data['geo']['city'] + ", "
                if 'postalCode' in data['geo']:
                    loc += data['geo']['postalCode'] + ", "
                if 'state' in data['geo']:
                    loc += data['geo']['state'] + ", "
                if 'country' in data['geo']:
                    loc += data['geo']['country']
                evt = SpiderFootEvent("PHYSICAL_ADDRESS", loc, self.__name__, event)
                self.notifyListeners(evt)
        except Exception:
            self.sf.debug("Unable to extract location from JSON.")
            pass

        try:
            if "company" in data:
                if 'domainAliases' in data['company']:
                    for d in data['company']['domainAliases']:
                        evt = SpiderFootEvent("AFFILIATE_INTERNET_NAME", d,
                                              self.__name__, event)
                        self.notifyListeners(evt)

                if 'site' in data['company']:
                    if 'phoneNumbers' in data['company']['site']:
                        for p in data['company']['site']['phoneNumbers']:
                            evt = SpiderFootEvent("PHONE_NUMBER", p, self.__name__, event)
                            self.notifyListeners(evt)
                    if 'emailAddresses' in data['company']['site']:
                        for e in data['company']['site']['emailAddresses']:
                            evt = SpiderFootEvent("EMAILADDR", e, self.__name__, event)
                            self.notifyListeners(evt)

                # Get the location of the person, also indicating
                # the location of the employer.
                if 'geo' in data['company']:
                    loc = ""

                    if 'streetNumber' in data['company']['geo']:
                        loc += data['company']['geo']['streetNumber'] + ", "
                    if 'streetName' in data['company']['geo']:
                        loc += data['company']['geo']['streetName'] + ", "
                    if 'city' in data['company']['geo']:
                        loc += data['company']['geo']['city'] + ", "
                    if 'postalCode' in data['company']['geo']:
                        loc += data['company']['geo']['postalCode'] + ", "
                    if 'state' in data['company']['geo']:
                        loc += data['company']['geo']['state'] + ", "
                    if 'country' in data['company']['geo']:
                        loc += data['company']['geo']['country']
                    evt = SpiderFootEvent("PHYSICAL_ADDRESS", loc, self.__name__, event)
                    self.notifyListeners(evt)
        except Exception:
            self.sf.debug("Unable to company info from JSON.")
            pass

# End of sfp_clearbit class
