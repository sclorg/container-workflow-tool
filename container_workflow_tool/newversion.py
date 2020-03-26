#! /usr/bin/python3
# newversion command

import subprocess as sub
from os import system
from re import findall
def create_newversion(_version):
	system('tput setaf 2')
	print('[*] Creating new version')
	a=sub.call(['mkdir',_version])

     
def move_version(_oldversion,_version):
	create_newversion()
	b=sub.call(['cp -r ',_oldversion,_version])
	sub.call(['rm -rf ',_oldversion,'/.git'])


	

	