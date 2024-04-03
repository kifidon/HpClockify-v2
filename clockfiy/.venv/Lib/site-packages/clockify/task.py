import logging
logging.basicConfig(level=logging.INFO)
from .abstract_clockify import AbstractClockify
# Activity developed by a Team member
class Task(AbstractClockify):

	def __init__(self,api_key):
		super(Task,self).__init__(api_key=api_key)	
	
	# create a new task in a project
	def add_new_task(self,workspace_id,project_id,task_name,assigneeId): 
		try:
			logging.info("Start function: add_new_task")

			url = self.base_url+'workspaces/'+workspace_id+'/projects/'+project_id+'/tasks/'
			task = None
			if (assigneeId == None):
				task =  {'name': task_name, 'projectId': project_id }   
			else:
				task =  {'name': task_name, 'projectId': project_id, 'assigneeId': assigneeId}   

			return self.request_post(url, task)
		except Exception as e: 
			logging.error("OS error: {0}".format(e))
			logging.error(e.__dict__) 
	
	def __get_task(self, url):
		try:
			all_tasks = []
			next = True
			page = 0
			urlx = url
			while (next):
				tasks = self.request_get(urlx)
				if len(tasks) == 0:
					next = False
				for task in tasks:
					if task in all_tasks:
						next = False
						break
					all_tasks.append(task)
				page = page + 1  
				urlx = url + "?page="+str(page)
			return all_tasks
		except Exception as e:
			logging.error("Error: {0}".format(e))
			logging.error(e.__dict__)

	# returns all done tasks
	def get_task_done(self,workspace_id,project_id): 
		try:
			
			logging.info("Start function: get_task_done")
			url = self.base_url+'workspaces/'+workspace_id+'/projects/'+project_id+'/tasks/'
			return self.__get_task(url)

		except Exception as e: 
			logging.error("OS error: {0}".format(e))
			logging.error(e.__dict__) 
	
	# returns all active tasks
	def get_task_active(self,workspace_id,project_id): 
		try:
			logging.info("Start function: get_task_active")
			url = self.base_url+'workspaces/'+workspace_id+'/projects/'+project_id+'/tasks/?is-active=True'
			return self.__get_task(url)
		except Exception as e: 
			logging.error("OS error: {0}".format(e))
			logging.error(e.__dict__) 
