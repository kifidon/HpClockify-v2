import factory
from .client import Client
from .project import Project
from .task import Task
from .workspace import Workspace
from .timeentry import TimeEntry
from .user import User
from .membership import Membership

class ClientFactory(factory.Factory):
	class Meta:
		model = Client
	
	api_key = None
		  
class ProjectFactory(factory.Factory):
	class Meta:
		model = Project
	
	api_key = None
		  
class TaskFactory(factory.Factory):
	class Meta:
		model = Task
	
	api_key = None
		  
class WorkspaceFactory(factory.Factory):
	class Meta:
		model = Workspace
	api_key = None
		  
class TimeEntryFactory(factory.Factory):
	class Meta:
		model = TimeEntry
	api_key = None
		  
class UserFactory(factory.Factory):
	class Meta:
		model = User
	api_key = None
		  
class MembershipFactory(factory.Factory):
	class Meta:
		model = Membership
	api_key = None	  

