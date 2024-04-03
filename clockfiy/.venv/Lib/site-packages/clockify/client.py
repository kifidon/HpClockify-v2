import logging
logging.basicConfig(level=logging.INFO)
from .abstract_clockify import AbstractClockify
# Client of project
class Client(AbstractClockify):

	def __init__(self,api_key):
		super(Client,self).__init__(api_key=api_key)