import logging
logging.basicConfig(level=logging.INFO)
from .abstract_clockify import AbstractClockify

# Project has one or more Tasks performed by Users connected to the Project through Membership
class Project(AbstractClockify):

	def __init__(self,api_key):
		super(Project,self).__init__(api_key=api_key)
		
	# returns all project from a workspace
	def get_all_projects(self,workspace_id): 
		try:
			logging.info("Start function: get_all_projects")
			url = self.base_url+'workspaces/'+workspace_id+'/projects/'
			return self.request_get(url)
		except Exception as e: 
			logging.error("OS error: {0}".format(e))
			logging.error(e.__dict__) 
	
	# create a new project in a workspace
	def create_new_project(self,workspace_id,project_name): 
		try:
			logging.info("Start function: create_new_project")
			url = self.base_url+'workspaces/'+workspace_id+'/projects/'
			data = {
					'name': project_name,
					"clientId": "",
					"isPublic": "false",
					"estimate": {"estimate": "3600","type": "AUTO"},
					"color": "#f44336",
					"billable": "false"
					}
			return self.request_post(url, data)
		except Exception as e: 
			logging.error("OS error: {0}".format(e))
			logging.error(e.__dict__) 
