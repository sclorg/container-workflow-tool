import os
import subprocess as sub
import sys

class NewVersion(object):
    def __init__(self,_oldversion,_version):
    	self._oldversion=_oldversion
    	self._version=_version

    def move(_oldversion,_version):
    	sub.Popen(['git','mv',_oldversion,_version],stdout=sub.PIPE)
    	sub.call('git commit -m "Added new version %s"'%_version,shell=True)


    def copyadd(_oldversion,_version):
    	sub.Popen(['cp','-r',_version,_oldversion],stdout=sub.PIPE)
    	sub.Popen(['git','add',_oldversion],stdout=sub.PIPE)
    	sub.call('git commit -m "Added old version %s"'%_oldversion,shell=True)  

    if __name__ == '__main__':
    	_oldversion= sys.argv[1]
    	_version = sys.argv[2]
    	move(_oldversion,_version)
    	copyadd(_oldversion,_version)