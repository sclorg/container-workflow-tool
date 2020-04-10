import os
import subprocess as sub
import shutil

from git import Repo
from git.exc import GitCommandError

class NewVersion(object,):
	def __init__(self,_oldversion,_version):
		self._oldversion=_oldversion
		self._version=_version

	def create_newversion(_version):
		system('tput setaf 2')
	    print('[*] Creating new version')
	    sub.call(['mkdir',self._version])


    def move_version(_oldversion,_version):
    	create_newversion()
	    sub.call(['git mv ',self._oldversion,self._version])
	    sub.run(['git commit'],shell=true)


    def new_commit(_oldversion,_version):
    	move_version()
    	sub.call(['cp -r',self._version,self._oldversion])
    	sub.call(['git add',self._version])
    	sub.run(['git commit'],shell=true)
    	