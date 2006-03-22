import commands, os, time

from listeners import NullResultListener, ConsoleResultListener
from testfarmserver import * #TODO provisional

class TestFarmClient :
	# Attributes : repositories[]
	
	def __init__(self, 
		name = '--unnamed_client--',
		repositories=[], 
		listeners=[ ConsoleResultListener() ],
		continuous=False,
		use_pushing_server=False,
	) :
		self.repositories = repositories
		self.listeners = listeners
		self.name = name

		if use_pushing_server :
			serverlistener = ServerListener( client_name=self.name )
			server_to_push = TestFarmServer()
			self.listeners.append( serverlistener )
		else:
			server_to_push = None

		while True :
			for repo in self.repositories :
				new_commits_found = repo.do_checking_for_new_commits( self.listeners )
				if not new_commits_found:
					print "!!!!!!!!!!!!! in idle stat. skipping this repository"
					if use_pushing_server: 
						server_to_push.update_static_html_files()
					print "sleeping %d seconds" % repo.seconds_idle
					time.sleep( repo.seconds_idle )
					continue
				repo.do_tasks( self.listeners, server_to_push = server_to_push )
				if use_pushing_server : 
					server_to_push.update_static_html_files()
			if not continuous: break
		
	def num_repositories(self) :
		return len( self.repositories )


def get_command_and_parsers(maybe_dict):
	info_parser = None
	stats_parser = None
	status_ok_parser = None 
	try:
		cmd = 'echo no explicit command provided'
		if maybe_dict.has_key(CMD) :
			cmd = maybe_dict[CMD] 
		if maybe_dict.has_key(INFO) :
			info_parser = maybe_dict[INFO]
		if maybe_dict.has_key(STATS) :
			stats_parser = maybe_dict[STATS]
		if maybe_dict.has_key(CD) :
			destination_dir = maybe_dict[CD]
			os.chdir( destination_dir )
		if maybe_dict.has_key(STATUS_OK) :
			status_ok_parser = maybe_dict[STATUS_OK]
	except AttributeError:
		cmd = maybe_dict
	return (cmd, info_parser, stats_parser, status_ok_parser)

class Task:
	def __init__(self, name, commands):
		self.name = name
		self.commands = commands

	def __begin_task(self, listeners):
		for listener in listeners :
			listener.listen_begin_task( self.name )

	def __end_task(self, listeners):
		for listener in listeners :
			listener.listen_end_task( self.name )
	
	def __send_result(self, listeners, cmd, status, output, info, stats):		
		for listener in listeners :
			listener.listen_result( cmd, status, output, info, stats )


	def do_task(self, listeners = [ NullResultListener() ] ):
		self.__begin_task(listeners)
		initial_working_dir = os.path.abspath(os.curdir)
		for maybe_dict in self.commands :
			cmd, info_parser, stats_parser, status_ok_parser = get_command_and_parsers(maybe_dict)
			temp_file = "%s/current_dir.temp" % initial_working_dir #TODO multiplatform
			cmd_with_pwd = cmd + " && pwd > %s" % temp_file
			exit_status, output = commands.getstatusoutput(cmd_with_pwd)
			if status_ok_parser :
				status_ok = status_ok_parser( output ) #TODO assert that returns a boolean
			else:
				status_ok = (exit_status == 0)
			if info_parser :
				info = info_parser(output)
			else :
				info = ''
			if stats_parser :
				stats = stats_parser(output)
			else:
				stats = {}
			if status_ok :
				output = ''
			self.__send_result(listeners, cmd, status_ok, output, info, stats)
			current_dir = open( temp_file ).read().strip()
			os.chdir( current_dir )
			if not status_ok :
				self.__end_task(listeners)
				os.chdir ( initial_working_dir )
				return False
		self.__end_task(listeners)
		os.chdir ( initial_working_dir )
		return True

class Repository :
	# Attributes : name, tasks[], deployment_task[] 

	def __init__(self, name = '-- unnamed repository --'): 
		self.name = name;
		self.tasks = []
		self.deployment_task = None
		self.not_idle_checking_cmd = ""
		self.seconds_idle = 0
		
	def get_name(self):
		return self.name;
		
	def get_num_tasks(self): # Note : Deployment task is considered as a separated task
		return len( self.tasks )
	
	def add_checking_for_new_commits(self, checking_cmd, minutes_idle = 5 ):
		self.not_idle_checking_cmd = checking_cmd
		self.seconds_idle = minutes_idle * 60

	def add_deployment_task(self, commands): #TODO abort if fails
		self.add_task("Deployment Task", commands)

	def add_task(self, taskname, commands):
		self.tasks.append(Task(taskname, commands)) 

	def do_checking_for_new_commits(self, listeners):
		if not self.not_idle_checking_cmd :
			new_commits_found = True #default
		else :
			zero_if_new_commits_found, output = commands.getstatusoutput( self.not_idle_checking_cmd )
			new_commits_found = not zero_if_new_commits_found
		for listener in listeners :
			listener.listen_found_new_commits( new_commits_found, self.seconds_idle )
		return new_commits_found

	def do_tasks( self, listeners = [ NullResultListener() ], server_to_push = None): #TODO remove server_to_push.
		all_ok = True
		for listener in listeners:
			listener.listen_begin_repository( self.name )
		for task in self.tasks :
			current_result = task.do_task(listeners)
			all_ok = all_ok and current_result
			if server_to_push : #TODO remove. this is just provisional. Is it?
				server_to_push.update_static_html_files()
		for listener in listeners:
			listener.listen_end_repository( self.name, all_ok )
		return all_ok
CMD = 1
INFO = 2
STATS = 3
CD = 4
STATUS_OK = 5
