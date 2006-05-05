#
#  Copyright (c) 2006 Pau Arumi, Bram de Jong, Mohamed Sordo 
#  and Universitat Pompeu Fabra
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#

import commands, os, time, sys, subprocess, tempfile

from listeners import NullResultListener, ConsoleResultListener
from testfarmserver import * 
from serverlistenerproxy import ServerListenerProxy

def is_string( data ):
	try: # TODO : find another clean way to tho this check 
		data.isalpha()
		return True
	except AttributeError:
		return False
	
class Runner :
	def __init__(self, 
		task,
		continuous=False,
		local_base_dir = None,	
		remote_server_url = None,
		verbose = False,
		testinglisteners = []

	) :
		
		self.listeners = [ ConsoleResultListener() ]

		serverlistener = None # for keyboard interrupt purpose

		if remote_server_url:
			listenerproxy = ServerListenerProxy(
				client_name=name, 
				service_url=remote_server_url,
				task_name=task.name
			)		
			self.listeners.append( listenerproxy )
		if local_base_dir :	
			serverlistener = ServerListener( 
				client_name=task.client_name, 
				logs_base_dir=local_base_dir + "/logs",
				project_name=task.project_name
			)
			self.listeners.append( serverlistener )
			server_to_push = TestFarmServer( 
				logs_base_dir=local_base_dir + "/logs", 
				html_base_dir=local_base_dir + "/html", 
				project_name=task.project_name )

		else:
			server_to_push = None

		if testinglisteners:
			self.listeners = testinglisteners

		try :
			#do_subtasks at lease one time	
			task.do_checking_for_new_commits( self.listeners, verbose=verbose ) #this creates a valid .idle file
			task.do_subtasks( self.listeners, server_to_push = server_to_push, verbose=verbose )

			while continuous :
				new_commits_found = task.do_checking_for_new_commits( self.listeners, verbose=verbose )
				if new_commits_found:
					task.do_subtasks( self.listeners, server_to_push = server_to_push, verbose=verbose )
				else:
					if server_to_push: #update idle time display
						server_to_push.update_static_html_files()
					time.sleep( task.seconds_idle )
		except KeyboardInterrupt :
			task.stop_execution_gently(self.listeners, server_to_push = server_to_push)
		

def get_command_and_parsers(maybe_dict):
	info_parser = None
	stats_parser = None
	status_ok_parser = None 
	try:
		cmd = 'echo no command specified'
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


def run_command_with_log(command, verbose = True, logfilename = None, write_as_html = False):

	if verbose and logfilename:
		logFile = open(logfilename, "a")
		if write_as_html:
			logFile.write("<hr/>")
			logFile.write("<p><span style=\"color:red\">command</span>: %s</p>" % command)
			logFile.write("<p><span style=\"color:red\">output</span>:</p><pre>\n")
		else:
			logFile.write("-" * 60 + "\n")
			logFile.write("command: %s\n" % command)
			logFile.write("output:\n")
		logFile.flush()
	else:
		logFile = None	
	output = []	 
	pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

	while True:
		tmp = pipe.stdout.readline()	
		output.append( tmp )
		if tmp:
			if verbose:
				print tmp.strip()				
			if verbose and logFile:
				logFile.write(tmp)
				logFile.flush()						
		if pipe.poll() is not None:
			break	
	status = pipe.wait()
	
	if verbose and logFile:
		if write_as_html:
			logFile.write("</pre><p><span style=\"color:red\">status</span>: %d</p>" % status)
		else:
			logFile.write("status: %d\n" % status)
		logFile.flush()
		logFile.close()
	
	return (''.join(output), status)
	
	
def run_command(command, initial_working_dir, verbose=False):
	logfile = initial_working_dir + "/command_log.html"
	return run_command_with_log(command, verbose=verbose, logfilename=logfile, write_as_html=True)


class SubTask:
	def __init__(self, name, commands, mandatory = False):
		self.name = name
		self.commands = commands
		self.mandatory = mandatory

	def __begin_subtask(self, listeners):
		for listener in listeners :
			listener.listen_begin_subtask( self.name )

	def __end_subtask(self, listeners):
		for listener in listeners :
			listener.listen_end_subtask( self.name )

	def __begin_command(self, cmd, listeners):
		for listener in listeners :
			listener.listen_begin_command( cmd )

	#def __end_command(self, cmd, listeners):
	#	for listener in listeners :
	#		listener.listen_end_command( cmd )
	
	def __end_command(self, listeners, cmd, status, output, info, stats):		
		for listener in listeners :
			listener.listen_end_command( cmd, status, output, info, stats )

	def is_mandatory(self):
		return self.mandatory

	def do_subtask(self, listeners = [ NullResultListener() ] , server_to_push = None, verbose=False): #TODO : Refactor
		self.__begin_subtask(listeners)
		if server_to_push:
				server_to_push.update_static_html_files()
		initial_working_dir = os.path.abspath(os.curdir)
		temp_file = tempfile.NamedTemporaryFile()
		for maybe_dict in self.commands :
			# 1 : Create a temp file to save working directory
			cmd, info_parser, stats_parser, status_ok_parser = get_command_and_parsers(maybe_dict)	
			if sys.platform == 'win32': #TODO multiplatform
				cmd_with_pwd = cmd + " && cd > %s" % temp_file.name
			else:
				cmd_with_pwd = cmd + " && pwd > %s" % temp_file.name	
			# 2 : Begin command run 
			self.__begin_command(cmd, listeners)
			if server_to_push: #TODO
				server_to_push.update_static_html_files()
			output, exit_status = run_command(cmd_with_pwd, initial_working_dir, verbose=verbose)
			if status_ok_parser :
				status_ok = status_ok_parser( output ) #TODO assert that returns a boolean
			else:
				status_ok = exit_status == 0
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
			#self.__send_result(listeners, cmd, status_ok, output, info, stats)
						
			current_dir = temp_file.read().strip()
			if current_dir:
				os.chdir( current_dir )
			if not status_ok :
				self.__end_command(listeners, cmd, status_ok, output, info, stats)
				self.__end_subtask(listeners)
				temp_file.close()
				os.chdir ( initial_working_dir )
				return False
			# 3: End command run 
			self.__end_command(listeners, cmd, status_ok, output, info, stats)
			if server_to_push: #TODO
				server_to_push.update_static_html_files()
		self.__end_subtask(listeners)
		temp_file.close()
		os.chdir ( initial_working_dir )
		return True

class Task :
	# Attributes : name, subtasks[], deployment[] 

	def __init__(self, project, client, name = '-- unnamed task --'): 
		self.name = name;
		assert is_string(name), '< %s > is not a valid project name (should be a string)' % str(name)
		self.project_name = project
		assert is_string(client), '< %s > is not a valid client name (should be a string)' % str(name)
		self.client_name = client
		self.subtasks = []
		self.deployment = None
		self.not_idle_checking_cmd = ""
		self.seconds_idle = 0
		
	def get_name(self):
		return self.name;
		
	def get_num_subtasks(self): # Note : Deployment task is considered as a separated task
		return len( self.subtasks )
	
	def add_checking_for_new_commits(self, checking_cmd, minutes_idle = 5 ):
		self.not_idle_checking_cmd = checking_cmd
		self.seconds_idle = minutes_idle * 60

	def add_deployment(self, commands): #TODO must be unique
		self.add_subtask("Deployment", commands, mandatory = True)

	def add_subtask(self, subtaskname, commands, mandatory = False):
		self.subtasks.append(SubTask(subtaskname, commands, mandatory))

	def do_checking_for_new_commits(self, listeners, verbose=False):
		initial_working_dir = os.path.abspath(os.curdir)
		if not self.not_idle_checking_cmd :
			new_commits_found = True #default
		else :
			output, zero_if_new_commits_found = run_command( self.not_idle_checking_cmd, initial_working_dir, verbose=verbose )
			new_commits_found = not zero_if_new_commits_found
		for listener in listeners :
			listener.listen_found_new_commits( new_commits_found, self.seconds_idle )
		return new_commits_found

	def do_subtasks( self, listeners = [ NullResultListener() ], server_to_push = None, verbose=False): 
		all_ok = True
		for listener in listeners:
			listener.listen_begin_task( self.name )
		for subtask in self.subtasks :
			current_result = subtask.do_subtask(listeners, server_to_push, verbose=verbose)
			all_ok = all_ok and current_result
			if not current_result and subtask.is_mandatory() : # if it is a failing mandatory task, force the end of repository  
				break 
			if server_to_push :
				server_to_push.update_static_html_files()
		for listener in listeners:
			listener.listen_end_task( self.name, all_ok )
		if server_to_push : 
			server_to_push.update_static_html_files()
		return all_ok

	def stop_execution_gently(self, listeners = [], server_to_push = None): # TODO : Refactor, only for ServerListener
		for listener in listeners:
			listener.listen_end_task_gently(self.name)
		if server_to_push :
			server_to_push.update_static_html_files()
		pass 

CMD = 1
INFO = 2
STATS = 3
CD = 4
STATUS_OK = 5
