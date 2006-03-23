#! /usr/bin/python

from testfarmclient import *
import os

os.environ['LD_LIBRARY_PATH']='%s/clam-sandboxes/tlocal/lib:/usr/local/lib' % os.environ['PATH']
def filter_cvs_update( text ):
	dont_start_interr = lambda line : not line[0]=='?'
	result = filter(dont_start_interr, text.split('\n') )	
	return '\n'.join(result)
clam = Repository("CLAM")
clam.add_task("starting clam", ["echo foo"])
clam.add_checking_for_new_commits( 
	checking_cmd="cd $HOME/clam-sandboxes/testing-clam && cvs -nq up -dP | grep ^[UP]",  
	minutes_idle=5
)
clam.add_deployment_task( [
	"cd $HOME/clam-sandboxes",
#	"cvs co -d testing-clam CLAM",
	{ CMD: "cd testing-clam && cvs -q up -dP", INFO: filter_cvs_update },
	"cd $HOME/clam-sandboxes/testing-clam/scons/libs",
	"scons configure prefix=$HOME/clam-sandboxes/tlocal",
	"scons install",
	"scons install",
] )

clam.add_task("SMSTools installation", [
	"cd $HOME/clam-sandboxes",
#	"cvs co -d testing-smstools CLAM_SMSTools",
	"cd testing-smstools && cvs up -dP",
	"cd $HOME/clam-sandboxes/testing-smstools/scons/QtSMSTools",
	"scons clam_prefix=$HOME/clam-sandboxes/tlocal"
] )

clam.add_task("execute QTSMStools", [
	"cd $HOME/clam-sandboxes/testing-smstools/scons/QtSMSTools",
#	"./QtSMSTools"
] )

clam.add_task("NetworkEditor installation", [
	"cd $HOME/clam-sandboxes",
	"cvs co -d testing-neteditor CLAM_NetworkEditor",
	"cd testing-neteditor/scons",
	"scons clam_prefix=$HOME/clam-sandboxes/tlocal"
] )

clam.add_task("execute NetworkEditor", [
	"cd $HOME/clam-sandboxes/testing-neteditor/scons",
#	"./NetworkEditor"
] )


shared_dir = "/iua-data/temp/users/parumi/clam_testsfarm_logs"
local_dir = "%s/clam-sandboxes/testfarm_logs" % os.environ['HOME']

TestFarmClient( 
	"testing_machine_linux_breezy", 
	[clam ], 
	generated_html_path='./html-clam', 
	logs_path=local_dir,
	continuous=False 
)

