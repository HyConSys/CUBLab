#import requests
import httplib2
import json

class RESTApiClient():
    def __init__(self, url):
        self.url = url
        #self.session = requests.Session()
        #self.session.trust_env = False
        self.http = httplib2.Http()
    
    def restGETjson(self, query = ""):
        #return self.session.get(self.url + query).json()
        return json.loads(self.http.request(self.url, method="GET")[1])

    def restPUTjson(self, json_data):
        self.http.request(
            self.url,
            method='POST',
            headers={'Content-Type': 'application/json; charset=UTF-8'},
            body=json.dumps(json_data)
        )
        #self.session.put(self.url, json=json_data)

