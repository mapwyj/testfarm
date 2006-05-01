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

from testfarmclient import *
from listeners import *
from coloredtest import ColoredTestCase
import os, os.path


def helperCurrentDir() :
	return os.path.abspath(os.curdir)

class Tests_Task(ColoredTestCase):
	def test_do_task__single_command_successful(self):
		task = Task("task", ["echo hello"])
		self.assertEquals(True, task.do_task())
	
	def test_do_task__multiple_command_successful(self):
		task = Task("task", ["echo hello", "ls"])
		self.assertEquals(True, task.do_task())
		
	def test_do_task__single_command_fails(self):
		task = Task("task", ["ls non-existing-file"])
		self.assertEquals(False, task.do_task())
		
	def test_do_task__multiple_command__one_fails(self):
		task = Task("task", ["ls", "ls non-existing-file", "echo hello"])
		self.assertEquals(False, task.do_task())

	## Results test
	def test_results_log__with_no_commands(self):
		task = Task("task name", [])
		listener = DummyResultListener()
		task.do_task( [listener] )
		self.assertEquals("""\
BEGIN_TASK task name
END_TASK task name""" , listener.log() )
	
	def test_results_log__single_command_ok(self):
		task = Task("task", ["echo hello"])
		listener = DummyResultListener()
		task.do_task( [listener] )
		self.assertEquals("""\
BEGIN_TASK task
BEGIN_CMD echo hello
('echo hello', 'ok', '', '', {})
END_CMD echo hello
END_TASK task""", listener.log() )
	
	def test_results_log__second_command_fails_so_exit(self):
		task = Task("task", ["echo hello", "non-existing-command", "ls"])
		listener = DummyResultListener()
		task.do_task( [listener] )
		self.assertEquals("""\
BEGIN_TASK task
BEGIN_CMD echo hello
('echo hello', 'ok', '', '', {})
END_CMD echo hello
BEGIN_CMD non-existing-command
('non-existing-command', 'failure', '/bin/sh: non-existing-command: command not found\\n', '', {})
END_CMD non-existing-command
END_TASK task""", listener.log() )
	
	def test_results_log__command_fails_with_stderr_and_stdout(self):
		task = Task("task", ["./write_to_stderr_and_stdout.py"])
		listener = DummyResultListener()
		task.do_task( [listener] )
		self.assertEquals("""\
BEGIN_TASK task
BEGIN_CMD ./write_to_stderr_and_stdout.py
('./write_to_stderr_and_stdout.py', 'failure', 'ERR OUT\\n', '', {})
END_CMD ./write_to_stderr_and_stdout.py
END_TASK task""", listener.log() )
		
	def test_results_log__of_two_listeners(self):
		task = Task("task", ["echo hello"])
		listener1 = DummyResultListener()
		listener2 = DummyResultListener()
		task.do_task( [listener1, listener2] )
		self.assertEquals("""\
BEGIN_TASK task
BEGIN_CMD echo hello
('echo hello', 'ok', '', '', {})
END_CMD echo hello
END_TASK task""", listener1.log() )
		self.assertEquals("""\
BEGIN_TASK task
BEGIN_CMD echo hello
('echo hello', 'ok', '', '', {})
END_CMD echo hello
END_TASK task""", listener2.log() )
	
	def test_command_saves_changed_working_dir(self): #TODO make portable
		task = Task("taskcd", ["cd /tmp", "pwd > /tmp/foo"])
		task.do_task()
		self.assertEquals( "/tmp", open("/tmp/foo").read().strip() )
	
	def test_new_task_with_default_working_dir(self): #TODO make portable
		initial_directory = helperCurrentDir()
		task = Task("taskcd", ["cd /tmpXX"])
		task.do_task()
		self.assertEquals( initial_directory, helperCurrentDir() )
	
	# command map
	def test_info_parser(self):
		id = lambda text: text
		task = Task("task", [{CMD: "echo hello", INFO: id}])
		listener = DummyResultListener()
		task.do_task([listener])
		self.assertEquals( """\
BEGIN_TASK task
BEGIN_CMD echo hello
('echo hello', 'ok', '', 'hello\\n', {})
END_CMD echo hello
END_TASK task""", listener.log())

	def test_stats_parser(self):
		outlen = lambda text: {'len': len(text)} 
		task = Task("task", [{CMD: "echo hello", STATS: outlen}])
		listener = DummyResultListener()
		task.do_task([listener])
		self.assertEquals( """\
BEGIN_TASK task
BEGIN_CMD echo hello
('echo hello', 'ok', '', '', {'len': 6})
END_CMD echo hello
END_TASK task""", listener.log())

	def test_cd(self):
		id = lambda text: text
		previousdir= helperCurrentDir() 
		task = Task("task", [{CMD: 'pwd', INFO: id, CD: '/tmp'}])
		listener = DummyResultListener()
		task.do_task([listener])
		self.assertEquals( """\
BEGIN_TASK task
BEGIN_CMD pwd
('pwd', 'ok', '', '/tmp\\n', {})
END_CMD pwd
END_TASK task""", listener.log() )

	def test_status_ok(self):
		parseError = lambda text: not ('error' in text)
		previousdir= helperCurrentDir() 
		task = Task("task", [{CMD: 'echo error', STATUS_OK: parseError}])
		listener = DummyResultListener()
		task.do_task([listener])
		self.assertEquals( """\
BEGIN_TASK task
BEGIN_CMD echo error
('echo error', 'failure', 'error\\n', '', {})
END_CMD echo error
END_TASK task""", listener.log() )


