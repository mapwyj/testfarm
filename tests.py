#! /usr/bin/python
# -*- coding: iso-8859-15 -*-

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

import unittest
from testfarmclient import *
from test_task import Tests_Task
from test_repository import Tests_Repository
from test_testfarmclient import Tests_TestFarmClient
from test_testfarmserver import Tests_TestFarmServer, Tests_ServerListener	

def main():
	unittest.main()

if __name__ == '__main__':
	main()

