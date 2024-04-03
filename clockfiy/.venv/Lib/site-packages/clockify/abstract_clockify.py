import requests
import json
import logging
import time
logging.basicConfig(level=logging.INFO)
from abc import ABC

class AbstractClockify(ABC):
    def __init__(self,api_key):

        self.base_url = 'https://api.clockify.me/api/' 
        self.api_key = api_key
        self.header =  {'X-Api-Key': self.api_key }
    
    def request_get(self,url):
        while (True):
            try:
                response = requests.get(url, headers=self.header)
                return response.json()
            except Exception as e:
                logging.error("Error: {0}".format(e))
                logging.error("Try againg in 60 seconds")
                time.sleep(60)
    
    def request_post(self,url,payload):
        while (True):
            try:
                response = requests.post(url, headers=self.header,json=payload)
                return response.json()
            except Exception as e:
                logging.error("Error: {0}".format(e))
                logging.error("Try againg in 60 seconds")
                time.sleep(60)