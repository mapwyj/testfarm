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

import datetime, os, glob, sys
import subprocess
 
header_index = """
<html>
<head>
<meta http-equiv="refresh" content="120">
<link href="style.css" rel="stylesheet" type="text/css">
<title>Tests Farm for project %(repository_name)s </title>
</head>
<body>
<h1>testfarm for project %(repository_name)s </h1>

"""

header_details = """
<html>
<head>
<link href="style.css" rel="stylesheet" type="text/css">
<title>Tests Farm Details</title>
<script type="text/javascript" language="JavaScript" src="testfarm.js"></script>
</head>
<body>
"""

footer = """
<div class="about">
<p>TestFarm is free software. Learn <a href="http://www.iua.upf.es/~parumi/testfarm">about TestFarm</a>.</p>
</div>
</body>
</html>
"""

def remove_path_and_extension( path ):
	return os.path.splitext( os.path.basename( path ) )[0]

def log_filename(logs_base_dir, repository_name, client_name) :
	return '%s/%s/%s.testfarmlog' % (logs_base_dir, repository_name, client_name)

def idle_filename(logs_base_dir, repository_name, client_name) :
	return '%s/%s/%s.idle' % (logs_base_dir, repository_name, client_name)

def create_dir_if_needed(dir):
	if not os.path.isdir( dir ) :
#		sys.stderr.write("\nWarning: directory '%s' is not available. Creating it." % dir)
		os.makedirs(dir)

#
#  LISTENER
#

class ServerListener:
	def __init__(self, 
		client_name='testing_client', 
		logs_base_dir = '/tmp/testfarm_tests',
		repository_name=None
	) :
		self.executions_needs_update = True
		self.client_name = client_name
		self.repository_name = repository_name
		self.logs_base_dir = logs_base_dir
		self.logfile = None
		self.idle_file = None
		
		assert repository_name, "Error, repository_name was expected"

		create_dir_if_needed( "%s/%s" % (self.logs_base_dir, repository_name) ) 
		self.logfile = log_filename( self.logs_base_dir, repository_name, self.client_name )
		self.idle_file = idle_filename( self.logs_base_dir, repository_name, self.client_name )

		
	def __append_log_entry(self, entry) :
		f = open(self.logfile, 'a+')
		f.write( entry )
		f.close()
	def __write_idle_info(self, idle_info) :
		f = open(self.idle_file, 'w')
		f.write( idle_info )
		f.close()

	def clean_log_files(self):
		subprocess.call('rm -rf %s' % self.logs_base_dir, shell=True)

	def current_time(self):
		return datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

	def listen_end_command(self, command, ok, output, info, stats):
		entry = str( ('END_CMD', command, ok, output, info, stats) ) + ',\n'
		self.__append_log_entry(entry)

	def listen_begin_command(self, cmd):
		entry = "('BEGIN_CMD', '%s'),\n" % cmd 
		self.__append_log_entry(entry)
	
	#def listen_end_command(self, cmd):
	#	entry = "('END_CMD', '%s'),\n" % cmd
	#	self.__append_log_entry(entry)

	def listen_begin_task(self, taskname):
		entry = "('BEGIN_TASK', '%s'),\n" % taskname 
		self.__append_log_entry(entry)

	def listen_end_task(self, taskname):
		entry = "('END_TASK', '%s'),\n" % taskname
		self.__append_log_entry(entry)
	
	def listen_begin_repository(self, repository_name):
		entry = "\n('BEGIN_REPOSITORY', '%s', '%s'),\n" % (repository_name, self.current_time())
		self.executions_needs_update = True
		self.__append_log_entry(entry)

	def listen_end_repository(self, repository_name, status):
		entry = "('END_REPOSITORY', '%s', '%s', '%s'),\n" % (repository_name, self.current_time(), status)
		self.__append_log_entry(entry)
		self.executions_needs_update = True

	def executions_updated(self):
		self.executions_needs_update = False
	
	def listen_found_new_commits(self,  new_commits_found, next_run_in_seconds ):
		idle_dict = {}
		idle_dict['new_commits_found'] = new_commits_found
		idle_dict['date'] = self.current_time()
		idle_dict['next_run_in_seconds']=next_run_in_seconds	
		self.__write_idle_info( str( idle_dict ) )
	
	def __get_last_task_name(self, log): # TODO: make static | LOG already reversed by listen_stop_repository_gently
		log.reverse()
		for entry in log :
			tag = entry[0]
			if tag == 'BEGIN_TASK' :
				task_name = entry[1]
				log.reverse()
				return  task_name
		assert "BEGIN_TASK not found"
		
	def listen_end_repository_gently(self, repository_name): #TODO: Refactor 
		append_entry = "('END_REPOSITORY', '%s', '%s', 'Aborted'),\n" % (repository_name, self.current_time())
		self.__append_log_entry(append_entry)	
			

#
#     SERVER
#
class TestFarmServer:
	def __init__(self, 
		logs_base_dir = '/tmp/testfarm_tests',
		html_base_dir = '/tmp/testfarm_html',
		repository_name = None
	) :
		self.logs_base_dir = logs_base_dir 
		self.html_base_dir = html_base_dir
		create_dir_if_needed( html_base_dir )
		if repository_name: #TODO not very sure of this  (PA)
			create_dir_if_needed( '%s/%s' % (html_base_dir, repository_name) )
			self.repository_name = repository_name
		else:
			print 'Warning: html dir was not created because Server was not initialized with a repository_name'
	
		
	def client_names(self):
		assert self.repository_name, "Error, repository_name was expected. But was None"
		logfiles = glob.glob('%s/%s/*.testfarmlog' % (self.logs_base_dir, self.repository_name) )
		result = map( remove_path_and_extension, logfiles)
		return result

	def load_client_log(self, client_name):
		filename = log_filename( self.logs_base_dir, self.repository_name, client_name )
		return eval("[ %s ]" % open( filename ).read() )

	def load_client_idle(self, client_name):
		filename = idle_filename( self.logs_base_dir, self.repository_name, client_name )
		try :
			content = open( filename ).read() 
		except IOError:
			return {}
		if not content :
			return {}
		return eval( content )

	def last_date(self, log):
		log.reverse()
		for entry in log :
			tag = entry[0]
			if tag == 'BEGIN_REPOSITORY':
				return entry[2]
		assert "BEGIN_REPOSITORY not found"

	def single_execution_details(self, client_name, wanted_date):
		log = self.load_client_log(client_name)
		result = []
		in_wanted_execution = False
		for entry in log :
			tag = entry[0]
			if not in_wanted_execution :
				if tag == 'BEGIN_REPOSITORY' and entry[2] == wanted_date :
					in_wanted_execution = True
			if in_wanted_execution :
				result.append(entry)
				if tag == 'END_REPOSITORY' :
					in_wanted_execution = False
					break
		return result

	def purge_client_logfile(self, client_name, last_date):
		log = self.load_client_log(client_name)
		date = ''
		prefix = '%s/%s' % (self.logs_base_dir, self.repository_name)
		logfilename = log_filename( self.logs_base_dir, self.repository_name, client_name )
		f = open(logfilename, 'w') #TODO maybe is dangerous !! (if somebody else is reading at the moment)
		for entry in log :
			tag = entry[0]
			if tag == 'BEGIN_REPOSITORY':
				assert entry[2] != date, "Error. found two repos with same date."
				date = entry[2]
				count = 1
				f.write('\n')
				print

			# write the maybe modified entry 
			if tag == 'END_CMD' and date != last_date:
				postfix = '%s_%s_%s' % (client_name, date, count)
				new_entry = self.__extract_info_and_output_to_auxiliar_file(entry, prefix, postfix)
				f.write( '%s,\n' % str(new_entry) )
				count += 1
			else :
				f.write( '%s,\n' % str(entry) )
		f.close()
		
	def __extract_info_and_output_to_auxiliar_file( self, cmd_tuple, prefix, postfix ):
		extracted_msg = '[SAVED TO FILE]'
		output = cmd_tuple[3]
		info = cmd_tuple[4]
		if output and output != extracted_msg :
			filename = '%s/purged_output__%s' % (prefix, postfix)
			f = open(filename, 'w')
			f.write(output)
			f.close()
			output = extracted_msg
		else:
			pass
		#	print 'dont extract output: ', output

		if info and info != extracted_msg :
			filename = '%s/purged_info__%s' % (prefix, postfix)
			f = open(filename, 'w')
			f.write(info)
			f.close()
			info = extracted_msg
		else:
			pass
		#	print 'dont extract output: ', output
		return (
			cmd_tuple[0], # tag END_CMD 
			cmd_tuple[1], # "the" cmd
			cmd_tuple[2], # status
			output,
			info,
			cmd_tuple[5] # stats
			)	

	def __html_single_execution_details(self, client_name, wanted_date):
		content = []
		id_info = 1; # auto-increment id
		id_output = 1; # auto-increment id
		opened_cmd = False # check if last command in log is already opened
		opened_task = False
		opened_repository = False
		for entry in self.single_execution_details(client_name, wanted_date ):
			tag = entry[0]
			if tag == 'BEGIN_REPOSITORY':
				content.append('<div class="repository"> BEGIN_REPOSITORY "%s" %s' % (entry[1], entry[2]) )
				opened_repository = True
			elif tag == 'BEGIN_TASK':
				content.append('<div class="task"> BEGIN_TASK "%s"' % entry[1])
				opened_task = True
			elif tag == 'BEGIN_CMD':
				content.append( '<div class=command>' )
				content.append( '<span class="command_string"> %s</span>' % entry[1] )
				opened_cmd = True						
			elif tag == 'END_TASK':
				content.append('END_TASK "%s"</div>' % entry[1])
				opened_task = False
			elif tag == 'END_REPOSITORY':
				if opened_cmd:
					content.append( '<span class="command_failure">[FAILURE]</span>' )
					content.append( '<p class="output"> command execution aborted by the client</p>')
					content.append('</div>')
				if opened_task:
					content.append('</div>')
				content.append( 'END_REPOSITORY "%s" %s %s</div>' % ( entry[1], entry[2], entry[3]) )
				return header_details + '\n'.join(content) + footer	
			else:
				assert tag == 'END_CMD', 'Log Parsing Error. Expected END_CMD, but was:' + entry

				if entry[2]:
					content.append( '<span class="command_ok">[OK]</span>' )
				else:
					content.append( '<span class="command_failure">[FAILURE]</span>' )
					content.append( '<p id="output%d" class="output"> OUTPUT: %s </p>' % ( id_output, entry[3] ) )
					content.append( ' <script type="text/javascript">togglesize(\'output%d\');</script> ' % id_output )
					id_output += 1
				if entry[4] :
					content.append( '<p id="info%d" class="info"> INFO: %s </p>' % ( id_info, entry[4] ) )
					content.append( ' <script type="text/javascript">togglesize(\'info%d\');</script> ' % id_info )
					id_info += 1
				if entry[5] :
					content.append(  '<p class="stats"> STATS: {%s} </p>' % ''.join(entry[5]) )
				content.append( '</div>' )
				opened_cmd = False
		
		if opened_cmd :
			content.append( '<span class="command_inprogress">in progress ...</span>' )
			content.append( '</div>')
		if opened_task :
			content.append( '</div>')
		if opened_repository :	
			content.append( '</div>')
			
		return header_details + '\n'.join(content) + footer	

	#minimal version:
#	def html_single_execution_details(self, client_name, wanted_date):
#		content = ["<pre>"]
#		for entry in self.single_execution_details(client_name, wanted_date ):
#			content.append( "\n".join( map(str, entry) ) )	
#		content.append("</pre>")
#		return header_details + "\n".join(content) + footer

	def __write_details_static_html_file(self, client_name, wanted_date):
		details = self.__html_single_execution_details(client_name, wanted_date)
		filename = "%s/%s/details-%s-%s.html" % (
			self.html_base_dir, 
			self.repository_name, 
			client_name, 
			wanted_date )
		f = open( filename, 'w' )
		f.write( details )
		f.close()
		return filename
	
	def __write_last_details_static_html_file(self):
		filenames = []
		for client in self.client_names():
			client_log = self.load_client_log(client)
			last_date = self.last_date(client_log)
			filename = self.__write_details_static_html_file(client, last_date)
 			self.purge_client_logfile(client, last_date) #TODO
			filenames.append(filename)
		return filenames

	def __get_client_executions(self, client_name): #TODO: MS - Refactor
		log = self.load_client_log(client_name)
		executions = []
		execution_opened = False
		for entry in  log :
			tag = entry[0]
			if tag == 'BEGIN_REPOSITORY' :
				repo_name = entry[1]
				begin_time = entry[2]
				execution_opened = True
			if tag == 'END_REPOSITORY' :
				end_time = entry[2]
				status_ok = entry[3]
				if status_ok == 'True' :
					status = 'stable'
				elif status_ok == 'Aborted' :
					status = 'aborted'
				else :
					status = 'broken'
				executions.append( (begin_time, end_time, repo_name, status) )
				execution_opened = False
		if execution_opened :
			executions.append( (begin_time, '', repo_name, 'inprogress') )
		executions.reverse()
		return executions

	def __collect_client_stats(self, client_name):
		log = self.load_client_log(client_name)
		allstats = {}
		begin_time = ''
		for entry in log :
			tag = entry[0]
			if tag == 'BEGIN_REPOSITORY':
				begin_time = entry[2]
			elif tag == 'BEGIN_TASK':
				current_task = entry[1]
			elif tag == 'END_CMD' :
				assert begin_time, "Error. found a stat before a begin_repository"
				stats_entry = entry[5]
				if not stats_entry:
					continue
				assert current_task, "Error. stats in an unamed task"
				if not allstats.has_key(current_task) :
					allstats[current_task] = []
				allstats[current_task].append( (begin_time, stats_entry) )
		return allstats

	def idle(self):
		result = {}
		for client_name in self.client_names():
			idle_entry = self.load_client_idle(client_name)
			result[client_name] = idle_entry
		return result

	def executions(self):
		result = {}
		for client_name in self.client_names():
			result[client_name] = self.__get_client_executions(client_name)
		return result

	def __html_format_client_executions(self, client_name, client_idle, client_executions):
		content = []
		time_tmpl = "%(hour)s:%(min)s:%(sec)s %(D)s/%(M)s"
		if client_idle and not client_idle['new_commits_found'] :
			idlechecktime_str = client_idle['date']
			client_idle['date'] = "<p>Last check done at : %s" % self.__format_datetime(
				idlechecktime_str, time_tmpl )
			content.append('''\
<div class="idle">
%(date)s
<p>Next run after %(next_run_in_seconds)s seconds </p>
</div>''' % client_idle)
		for begintime_str, endtime_str, repo_name, status in client_executions:
			name_html = "<p>%s</p>" % repo_name
			begintime_html = "<p>Begin time: %s </p>" % self.__format_datetime(begintime_str, time_tmpl)
			if endtime_str :					
				if status == "aborted" :
					endtime_html = "\n<p>Client Aborted: %s</p>" % self.__format_datetime(endtime_str, time_tmpl)
				else:
					endtime_html = "<p>End time: %s </p>" % self.__format_datetime(endtime_str, time_tmpl)
	
			else:
				endtime_html = "<p>in progres...</p>"
			details_html = '<p><a href="details-%s-%s.html">details</a></p>' % (client_name, begintime_str)
			content.append( '<div class="%s">\n%s\n%s\n%s\n%s\n</div>' % (
				status, name_html, begintime_html, endtime_html, details_html) )
		return content

	"""def __initialize_clients_in_day_executions(self, day_executions, executions_per_client): #TODO: rename method
		# we have to initialize all clients in a day even though they are not present in it 
		for day in day_executions :
			day_clients = day_executions[day]
			for client in executions_per_client.keys():
				if client not in day_clients:
					day_clients[client] = []	
		return day_executions
	"""

	def day_executions(self, executions_per_client):
		day_executions = {}
		# order executions per day
		time_tmpl = "%(Y)s-%(M)s-%(D)s"
		for client in executions_per_client.keys():
			client_executions = executions_per_client[client]
			for begintime_str, endtime_str, repo_name, status in client_executions:
				day = self.__format_datetime(begintime_str, time_tmpl)
				if day not in day_executions:
					day_executions[day] = {}
				if client not in day_executions[day]:
					day_executions[day][client] = []
		#		day_executions = self.__initialize_clients_in_day_executions(day_executions, executions_per_client)
				day_executions[day][client].append( (begintime_str, endtime_str, repo_name, status) )
		
	#	print "##################DICTIONARY FORMAT CLIENTS DAY ITERATIONS#######################"
	#	print day_executions
	#	print "#################################################################################"
	
		return day_executions

	def __html_format_clients_day_executions(self, idle_per_client, executions_per_day, all_clients): # TODO : MS Finish Implementation
		content = []
		# all_clients = self.client_names() DOES NOT WORK PROPERLY
		executions_per_day_key_sorted = executions_per_day.keys()
		executions_per_day_key_sorted.sort(reverse = True)
		html_time_tmpl = "%(D)s/%(M)s/%(Y)s"
		for day in executions_per_day_key_sorted :
			#content.append('<tr>')
			formatted_day = self.__format_datetime(day+'-00-00-00', html_time_tmpl)
			content.append('<tr><td colspan="%s" align="center">%s</td></tr><tr>' % (len(all_clients), formatted_day)) # insert a brake line
			day_clients = executions_per_day[day]
			for client in all_clients:
			#	print "CLIENT_KEY IN DAY CLIENTS = ", client
				content.append('<td>')
				client_executions = day_clients.get(client, []) # if client return client executions , else return empty list
			#	print "CLIENT_VALUE IN DAY CLIENTS = ", client_executions
				client_idle = idle_per_client[client]
				content += self.__html_format_client_executions(client, client_idle, client_executions) 
				content.append('</td>')
			content.append('</tr>')
		return content

	def __html_index(self, clients_with_stats):
		executions_per_client = self.executions()
		idle_per_client = self.idle()
		content = ['<table>\n<tr>']
		for client in executions_per_client.keys():
			content.append('<th> Client: %s </th>' % client )
		content.append('</tr>')

		content.append('<tr>')
		for client in executions_per_client.keys():
			if client in clients_with_stats:
				thumb_html = '<a href="%s-stats.html"><img src="%s_1-thumb.png" /></a> <a href="%s-stats.html">more...</a>' % (client, client, client)
				
			else:
				thumb_html = ''
			content.append('<td style="text-align:center"> %s </td>' % thumb_html)
		content.append('</tr>')	
		executions_per_day = self.day_executions(executions_per_client)
		content += self.__html_format_clients_day_executions(idle_per_client, executions_per_day, executions_per_client.keys())
		content.append('</table>')
		return header_index % {'repository_name':self.repository_name} + '\n'.join(content) + footer
		
	def __write_html_index(self, clients_with_stats):
		filename = "%s/%s/index.html" % (	
			self.html_base_dir, 
			self.repository_name )
		f = open( filename, 'w' )
		f.write( self.__html_index( clients_with_stats ) )
		f.close()
		return filename

	def __helper_apache_log(self, msg):
			from mod_python import apache
			apache.log_error('TestFarm:  '+ str(msg) )
		
	def update_static_html_files(self):
#		sys.stderr.write( 'update static html files' )
		newfiles, clients_with_stats = self.plot_stats()
		newfiles += self.__write_last_details_static_html_file()
		newfiles.append( self.__write_html_index( clients_with_stats ) )
		if self.repository_name == 'CLAM': #TODO the proper way
			filesstr = ' '.join(newfiles)
			out = subprocess.call('scp %s clamadm@www.iua.upf.es:testfarm/' % filesstr, shell=True)
#			self.__helper_apache_log('TestFarm: sended: %s \nout: %s ' % (filesstr, str(out)) )


	def collect_stats(self):
		result = {}
		for client in self.client_names():
			result[client] = self.__collect_client_stats(client)
		return result

	def __assert_all_keys_equal_length(self, stats, length):
		keys = stats.keys()
		for key in keys:
			assert length == len(stats[key]), "Error found stat with diferent length. key: %s\n%s" %(key, stats)

	def __format_datetime(self, time_str, pattern, time_tags = ["Y", "M", "D", "hour", "min", "sec"]) :
		time_dict = dict(zip( time_tags, time_str.split("-") ))
		return pattern % time_dict 

	def plot_stats(self): # TODO refactor extract methods
		allclients_stats = self.collect_stats()
		clients = allclients_stats.keys()
		images = []
		pngs = []
		pngs_thumb = []
		svgs = []
		clients_with_stats = []
		prefix_html = '%s/%s' % (self.html_base_dir, self.repository_name)
		prefix_logs = '%s/%s' % (self.logs_base_dir, self.repository_name)
		for client in clients:
			diagram_count = 0
			alltasks_stats = allclients_stats[ client ]	
			for task in alltasks_stats.keys():
				stats_list = alltasks_stats[task ]
				if stats_list :
					clients_with_stats.append( client )
				else:
					print '++++++++ found client without stats:', client #TODO remove
					continue

				diagram_count += 1

					
				# 1. collect all keys and remove spaces
				allkeys = set()
				for time, stat in stats_list:
					allkeys.update( stat.keys() )
				normalizedkeys = map(lambda x: '_'.join(x.split()), allkeys) #TODO this lambda should be global function

				# 2. write a line for each item in a list
				diagram_name = '%s_%d' % (client, diagram_count)
				plotfilename = '%s/%s.plot' % (prefix_logs, diagram_name)

				plotfile_content = ['time']
				for key in normalizedkeys :
					plotfile_content.append( '\t'+key )
				plotfile_content.append('\n')

				for time, stat in stats_list:
					plotfile_content.append( self.__format_datetime(time, "%(Y)s/%(M)s/%(D)s.%(hour)s:%(min)s") )
					for key in allkeys: 
						plotfile_content.append( '\t'+str( stat.get(key, '-') ) )
					plotfile_content.append('\n')

				# 3. write list to file
				f = open(plotfilename, 'w')
				f.writelines( plotfile_content )
				f.close()

				# 4. execute ploticus command
				columns = ""
				for i in range(len(allkeys)-1): # "y=1" already in the ploticus_cmd
					columns += " y%d=%d" % (i+2, i+3) # y2=3 y3=4, etc.

				png_filename = '%s/%s.png' % (prefix_html, diagram_name)
				png_thumbfilename = '%s/%s-thumb.png' % (prefix_html, diagram_name)
				svg_filename = '%s/%s.svg' % (prefix_html, diagram_name)
				
				#maybe use: 'xrange="2006/04/04.22:00 2006/04/05.12:00"'
				ploticus_cmd_tmpl = '''\
ploticus %s -prefab chron data=%s header=yes x=1 y=2 %s \
datefmt=yyyy/mm/dd  xinc="1 day" mode=line unittype=datetime\
title="some statistics (still experimental)" -o %s %s''' # + 'xrange="2006/04/06.20:35 2006/04/06.21:15"'

				cmd = ploticus_cmd_tmpl % ("-png", plotfilename, columns, png_filename, '')
				subprocess.call( cmd, shell=True) 

				cmd = ploticus_cmd_tmpl % ("-png", plotfilename, columns, png_thumbfilename, '-scale 0.3') 
				subprocess.call( cmd, shell=True) 

				cmd = ploticus_cmd_tmpl % ( "-svg", plotfilename, columns, svg_filename, '')
				subprocess.call( cmd, shell=True) 

				pngs.append('%s.png' % diagram_name)
				pngs_thumb.append('%s-thumb.png' % diagram_name)
				svgs.append('%s.svg' % diagram_name)
				images += [png_filename, png_thumbfilename, svg_filename]
			# write stats client page
			stats_html_filename = '%s/%s-stats.html' % (prefix_html, client)
			f = open(stats_html_filename, 'w')
			f.write('<html><body>\n')
			for png, svg in zip(pngs, svgs):
				f.write('<img src="%s"> <p><a href="%s">svg</a></p>\n' % (png, svg) )
			f.write('</body></html>\n')
			f.close()
			images.append(stats_html_filename)
		return images, clients_with_stats
					


		