import logging
logging.basicConfig(level=logging.INFO)
from .abstract_clockify import AbstractClockify
# A Workspace is an entity that groups Projects related to a Client.
class Workspace(AbstractClockify):

	def __init__(self,api_key):
		super(Workspace,self).__init__(api_key=api_key)
	
	# returns all workspace from a user
	def get_all_workspaces(self): 
		try:
			logging.info("Start function: get_all_workspaces")
			url = self.base_url+'workspaces/'
			return self.request_get(url)
			
		except Exception as e: 
			logging.error("OS error: {0}".format(e))
			logging.error(e.__dict__) 
	
	# create new worskspace
	def create_new_workspace(self,name): 
		try:
			logging.info("Start function: create_new_workspace")
			url = self.base_url+'workspaces/'
			data = {'name': name}
			return self.request_post(url, data)

		except Exception as e: 
			logging.error("OS error: {0}".format(e))
			logging.error(e.__dict__) 
