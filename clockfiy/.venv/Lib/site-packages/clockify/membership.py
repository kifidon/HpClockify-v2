import logging
logging.basicConfig(level=logging.INFO)
from .abstract_clockify import AbstractClockify
# An user in a Project
class Membership(AbstractClockify):

	def __init__(self,api_key):
		super(Membership,self).__init__(api_key=api_key)	
