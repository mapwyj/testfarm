#! /usr/bin/python

import sys
sys.path.append('../src')
from task import *
from project import Project
from client import Client
from runner import Runner
import os, time

start_time = -1
def start_timer(output):
	global start_time
	start_time = time.time()
def exectime_unittests(output):
	global start_time
	return {'exectime_unittests' : time.time() - start_time}
def exectime_functests(output):
	global start_time
	return {'exectime_functests' : time.time() - start_time}

def force_ok(output):
	return True

HOME = os.environ['HOME']
os.environ['LD_LIBRARY_PATH']='%s/clam-sandboxes/tlocal/lib:/usr/local/lib' % HOME

def filter_cvs_update( text ):
	dont_start_interr = lambda line : not line or not line[0]=='?'
	result = filter(dont_start_interr, text.split('\n') )	
	return '\n'.join(result)

def set_qtdir_to_qt4(x) :
	os.environ['QTDIR']='/usr/local/Trolltech/Qt-4.1.0/'
	os.environ['PKG_CONFIG_PATH']=os.environ['QTDIR']+'lib/pkgconfig'
def set_qtdir_to_qt3(x) :
	os.environ['QTDIR']='/usr/'

breezy = Client("linux_ubuntu_breezy")
breezy.brief_description = '<img src="http://clam.iua.upf.es/images/linux_icon.png"/> <img src="http://clam.iua.upf.es/images/ubuntu_icon.png"/>'
	

clam = Task(
	project = Project("CLAM"), 
	client = breezy, 
	task_name="with cvs update" 
	)
repositories = [
	"testing-clam",
	"testing-neteditor",
	"testing-smstools",
	"testing-annotator",
]

clam.set_check_for_new_commits( 
		checking_cmd="cd $HOME/clam-sandboxes && cvs -nq up -dP %s | grep ^[UP]" %
			 " ".join(repositories),  
		minutes_idle=5
)
clam.add_deployment( [
	{CMD: "echo setting QTDIR to qt3 path ", INFO: set_qtdir_to_qt3},
	"cd $HOME/clam-sandboxes/testing-clam",
	{CMD: "cvs -q up -dP", INFO: filter_cvs_update },
	"rm -rf $HOME/clam-sandboxes/tlocal/*",
	"cd $HOME/clam-sandboxes/testing-clam/scons/libs",
	"scons configure prefix=$HOME/clam-sandboxes/tlocal",
	"scons",
	"scons install",
] )
clam.add_subtask("Unit Tests (with scons)", [
	{CMD: "echo setting QTDIR to qt3 path ", INFO: set_qtdir_to_qt3},
	"cd $HOME/clam-sandboxes/testing-clam",
	"cd scons/tests",
	"scons test_data_path=$HOME/clam-sandboxes/CLAM-TestData clam_sconstools=$HOME/clam-sandboxes/testing-clam/scons/sconstools install_prefix=$HOME/clam-sandboxes/tlocal clam_prefix=$HOME/clam-sandboxes/tlocal", # TODO: test_data_path and release
	"cd unit_tests",
	{INFO : start_timer}, 
	{CMD: "./UnitTests", INFO: lambda x:x},
	{STATS : exectime_unittests},
] )
clam.add_subtask("Functional Tests (with scons)", [
	{CMD: "echo setting QTDIR to qt3 path ", INFO: set_qtdir_to_qt3},
	"cd $HOME/clam-sandboxes/testing-clam",
	"cd scons/tests",
	"scons test_data_path=$HOME/clam-sandboxes/CLAM-TestData clam_sconstools=$HOME/clam-sandboxes/testing-clam/scons/sconstools install_prefix=$HOME/clam-sandboxes/tlocal clam_prefix=$HOME/clam-sandboxes/tlocal", # TODO: test_data_path and release
	"cd functional_tests",
	{INFO : start_timer}, 
	{CMD:"./FunctionalTests", INFO: lambda x:x},
	{STATS : exectime_functests},
] )
clam.add_subtask("CLAM Examples (with scons)", [
	{CMD: "echo setting QTDIR to qt3 path ", INFO: set_qtdir_to_qt3},
	"cd $HOME/clam-sandboxes/testing-clam",
	"cd scons/examples",
	"scons clam_prefix=$HOME/clam-sandboxes/tlocal",
] )
clam.add_subtask("SMSTools installation", [
	{CMD: "echo setting QTDIR to qt3 path ", INFO: set_qtdir_to_qt3},
	"cd $HOME/clam-sandboxes/testing-smstools",
	{CMD: "cvs -q up -dP", INFO: filter_cvs_update },
	"scons clam_sconstools=$HOME/clam-sandboxes/testing-clam/scons/sconstools install_prefix=$HOME/clam-sandboxes/tlocal clam_prefix=$HOME/clam-sandboxes/tlocal",
	"scons install",
	"$HOME/clam-sandboxes/testing-clam/scons/sconstools/changeExampleDataPath.py $HOME/clam-sandboxes/tlocal/share/smstools ",
] )
'''
clam.add_subtask("execute QTSMStools", [
	"cd $HOME/clam-sandboxes/testing-smstools",
	"./QtSMSTools", #TODO run a while
] )
'''
clam.add_subtask("NetworkEditor installation", [
	{CMD: "echo setting QTDIR to qt3 path ", INFO: set_qtdir_to_qt3},
	"cd $HOME/clam-sandboxes/testing-neteditor",
	{CMD: "cvs -q up -dP", INFO: filter_cvs_update },
	"scons clam_sconstools=$HOME/clam-sandboxes/testing-clam/scons/sconstools install_prefix=$HOME/clam-sandboxes/tlocal clam_prefix=$HOME/clam-sandboxes/tlocal",
	"$HOME/clam-sandboxes/testing-clam/scons/sconstools/changeExampleDataPath.py $HOME/clam-sandboxes/tlocal/share/smstools ",
] )
'''
clam.add_subtask("execute NetworkEditor", [
	"cd $HOME/clam-sandboxes/testing-neteditor",
	"./NetworkEditor", #TODO run a while
] )
'''
clam.add_subtask('vmqt compilation and examples', [
	{CMD: "echo setting QTDIR to qt4 path ", INFO: set_qtdir_to_qt4},
	"cd $HOME/clam-sandboxes/testing-annotator/vmqt",
	{CMD: "cvs -q up -dP", INFO: filter_cvs_update },
	'scons clam_sconstools=$HOME/clam-sandboxes/testing-clam/scons/sconstools install_prefix=$HOME/clam-sandboxes/tlocal clam_prefix=$HOME/clam-sandboxes/tlocal release=1 double=1',
	'scons examples',
] )

clam.add_subtask("Annotator installation", [
	{CMD: "echo setting QTDIR to qt4 path ", INFO: set_qtdir_to_qt4},
	"cd $HOME/clam-sandboxes/testing-annotator",
	{CMD: "cvs -q up -dP", INFO: filter_cvs_update },
	"scons clam_vmqt4_path=vmqt clam_sconstools=$HOME/clam-sandboxes/testing-clam/scons/sconstools install_prefix=$HOME/clam-sandboxes/tlocal clam_prefix=$HOME/clam-sandboxes/tlocal",
	"scons install",
] )
'''
clam.add_subtask("execute Annotator", [
	"cd $HOME/clam-sandboxes/testing-annotator",
	"./Annotator" #TODO run a while
] )
'''
clam.add_subtask("Deploy OLD (srcdeps) build system", [
	"cd $HOME/clam-sandboxes/testing-clam/build/srcdeps",
	"make",
	"cd ..",
	"pwd && autoconf",
	"./configure"
	
])
clam.add_subtask("Unit Tests (with srcdeps)", [
	{CMD: "echo setting QTDIR to qt3 path ", INFO: set_qtdir_to_qt3},
	"cd $HOME/clam-sandboxes/testing-clam",
	"cd build/Tests/UnitTests",
	"make depend",
	"CONFIG=release make",
	{INFO : start_timer}, 
#	{CMD:"./UnitTests", INFO: lambda x : x},
	{CMD:"./UnitTests"},
	{STATS : exectime_unittests}

] )
clam.add_subtask("Functional Tests (with srcdeps)", [
	{CMD: "echo setting QTDIR to qt3 path ", INFO: set_qtdir_to_qt3},
	"cd $HOME/clam-sandboxes/testing-clam",
	"cd build/Tests/FunctionalTests",
	"make depend",
	"CONFIG=release make",
	{INFO : start_timer}, 
#	{CMD:"./FunctionalTests", INFO: lambda x : x},
	{CMD:"./FunctionalTests"},
	{STATS : exectime_functests}
] )

clam.add_subtask("Deploy SMSTools srcdeps branch for SMSBase tests", [
	"cd $HOME/clam-sandboxes",
	"rm -rf testing-smstools-srcdeps",
	"cvs co -r srcdeps-build-system-branch -d testing-smstools-srcdeps CLAM_SMSTools",
	'echo "CLAM_PATH=$HOME/clam-sandboxes/testing-clam/" > testing-smstools-srcdeps/build/clam-location.cfg'
] )

clam.add_subtask("Testing SMSTransformations (using SMSTools srcdeps branch)", [
	"cd $HOME/clam-sandboxes",
	"cd testing-smstools-srcdeps/build/FunctionalTests",
	"make depend",
	"CONFIG=debug make", #release doesn't work
	{CMD: "./SMSToolsTests", INFO: lambda x : x}
] )



Runner( clam, 
	continuous = True,
	remote_server_url = 'http://10.55.0.66/testfarm_server'
)

