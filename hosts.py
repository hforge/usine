# -*- coding: UTF-8 -*-
# Copyright (C) 2009-2010 Juan David Ibáñez Palomar <jdavid@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from the Standard Library
from contextlib import closing
from os.path import basename, expanduser
from stat import S_ISDIR
from sys import stdout

# Import from paramiko
from paramiko import AutoAddPolicy, SSHClient

# Import from itools
from itools.core import get_pipe


"""
This module provides a common interface to access the localhost and to
access a remote host (through paramiko).  The common API is:

- run: to execute a command

- put: to copy a file
"""



class LocalHost(object):

    cwd = None


    def chdir(self, cwd):
        self.cwd = expanduser(cwd)


    def run(self, command, cwd=None):
        # Change dir
        if cwd:
            self.chdir(cwd)
        # Format command
        if type(command) is str:
            command_str = command
            command = command.split()
        else:
            command_str = ' '.join(command)
        # Print
        print '%s $ %s' % (self.cwd, command_str)
        # Call
        return get_pipe(command, cwd=self.cwd)


    def put(self, source, target):
        raise NotImplementedError



class RemoteHost(object):

    def __init__(self, host, user):
        host, port = host.split(':')
        self.host = host
        self.port = int(port)
        self.user = user
        # Connection
        self.ssh = None


    def chdir(self, cwd):
        self.cwd = cwd


    @property
    def transport(self):
        if self.ssh is None:
            print 'Connect %s@%s:%s' % (self.user, self.host, self.port)
            ssh = SSHClient()
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(AutoAddPolicy())
            ssh.connect(self.host, self.port, self.user)
            self.ssh = ssh
        return self.ssh.get_transport()


    def close(self):
        if self.ssh:
            self.ssh.close()
            self.ssh = None


    def run(self, command, cwd=None, quiet=False):
        # Change dir
        if cwd:
            self.chdir(cwd)

        # Print
        if quiet is False:
            print '%s@%s %s $ %s' % (self.user, self.host, self.cwd, command)
        command = 'cd %s && %s' % (self.cwd, command)

        # Call
        channel = self.transport.open_channel('session')
        try:
            channel.exec_command(command)
            status = channel.recv_exit_status()
            if status:
                print 'ERROR'
                data = channel.recv_stderr(512)
                while data:
                    stdout.write(data)
                    stdout.flush()
                    data = channel.recv_stderr(512)
            else:
                data = channel.recv(512)
                while data:
                    stdout.write(data)
                    stdout.flush()
                    data = channel.recv(512)
        finally:
            channel.close()


    def put(self, source, target):
        ftp = self.transport.open_sftp_client()
        with closing(ftp) as ftp:
            target = target.replace('~', ftp.normalize('.'))
            statinfo = ftp.stat(target)
            if S_ISDIR(statinfo.st_mode):
                target = '%s/%s' % (target, basename(source))
            try:
                statinfo = ftp.stat(target)
            except IOError:
                msg = 'PUT %s -> %s@%s:%s'
                print msg % (source, self.user, self.host, target)
                ftp.put(source, target)
            else:
                filename = basename(source)
                print '[INFO] %s already uploaded, skipping.' % filename


# Singleton
local = LocalHost()

# Cache
remote_hosts = {}

def get_remote_host(host, user):
    key = (host, user)
    remote_host = remote_hosts.get(key)
    if not remote_host:
        remote_host = RemoteHost(host, user)
        remote_hosts[key] = remote_host

    return remote_host
