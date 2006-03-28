#
#  Copyright (c) 2006 Pau Arum�, Bram de Jong, Mohamed Sordo 
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

import sys

class NullResultListener : #TODO base class
	"Discards messages"
	def listen_result(self, command, ok, output, info, stats):
		pass
	def listen_begin_task(self, taskname):
		pass	
	def listen_end_task(self, taskname):
		pass	
	def listen_begin_repository(self, repositoryname):
		pass
	def listen_end_repository(self, repositoryname, status):
		pass
	def listen_found_new_commits( self, new_commits_found, seconds_idle ):
		pass

class DummyResultListener :
	"helper ResultListener class "
	def __init__(self):
		self.results = []

	def log(self) :
		return "\n".join( self.results )

	def listen_result(self, command, ok, output, info, stats):
		if ok :
			status_text = "ok"
		else :
			status_text = "failure"
		self.results.append( str( (command, status_text, output, info, stats) ) )

	def listen_begin_task(self, taskname):
		self.results.append( "BEGIN_TASK %s" % taskname )

	def listen_end_task(self, taskname):
		self.results.append( "END_TASK %s" % taskname )
	
	def listen_begin_repository(self, repositoryname):
		self.results.append( "BEGIN_REPOSITORY %s" % repositoryname )

	def listen_end_repository(self, repositoryname, status):
		self.results.append( "END_REPOSITORY %s" % repositoryname )
	
	def listen_found_new_commits( self, new_commits_found, seconds_idle ):
		pass


class ConsoleResultListener :
	def __init__(self):
		self.results = []

		self.colors = {
			'BOLD'  :"\x1b[01m",
			'RED'   :"\x1b[31;01m",
			'GREEN' :"\x1b[32;01m",
			'YELLOW':"\x1b[33;01m", # unreadable on white backgrounds
			#'YELLOW':"\033[1m", #"\033[93m" # unreadable on white backgrounds
			'CYAN'  :"\x1b[36;01m",
			'MAGENTA':"\x1b[35;01m", 
			'NORMAL':"\x1b[0m",
			}
			
	def color(self, name):
		if sys.platform == 'win32':
			return ""
	
		try:
			return self.colors[name]
		except:
			return ""

	def pprint(self, col, str, label=''):
		mycol = self.color(col)
		print "%s%s%s %s" % (mycol, str, self.color('NORMAL'), label)

	def pprint_cmd_result(self, cmd, status_ok, output, info, stats):
		cmd_color = self.color('CYAN')
		if status_ok:
			status_text = '[ ok ]'
			status_color = self.color('GREEN')
		else :
			status_text = "[ failure ]"
			status_color = self.color('RED')
		normal = self.color('NORMAL')
		output_color = normal
		yellow = self.color('YELLOW')
		if output :
			ending = '%s---------------------------------------------\n' % yellow
			ending += 'Output of failing command:%s\n\n%s\n' % (normal, output)
			ending += '%s\n---------------------------------------------%s\n' % (yellow, normal)
		else:
			ending = ''
		sys.stdout.write( " | %scmd:%s%60s\t\t%s%s%s\n | %sinfo:%s %s\n | %sstats:%s %s\n%s%s%s |\n" % (yellow, cmd_color, cmd, status_color, status_text, normal, yellow, normal, info, yellow, normal, stats, output_color, ending, normal) )


	def listen_result(self, command, ok, output, info, stats):
		self.pprint_cmd_result( command, ok, output, info, stats )

	def listen_begin_task(self, taskname):
		self.pprint('BOLD', "  BEGIN_TASK %s" % taskname )

	def listen_end_task(self, taskname):
		self.pprint ('BOLD', "  END_TASK %s\n" % taskname )
	
	def listen_begin_repository(self, repositoryname):
		self.pprint ('BOLD', "BEGIN_REPOSITORY %s\n" % repositoryname )

	def listen_end_repository(self, repositoryname, status):
		self.pprint ('BOLD', "END_REPOSITORY %s --> %s" % (repositoryname, status) )

	def listen_found_new_commits( self, new_commits_found, seconds_idle ):
		self.pprint('MAGENTA', 'New commits found, or No checks specified :', new_commits_found)
		self.pprint('MAGENTA', 'New check in %d seconds.' % seconds_idle)

