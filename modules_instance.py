#!/usr/bin/env python
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
from httplib import HTTPConnection
from os.path import expanduser

# Import from itools
from itools.core import freeze
from itools import vfs

# Import from usine
from config import config
from hosts import local, get_remote_host
from modules import module, register_module


class instance(module):

    def get_host(self):
        server = self.options['server']
        if server == 'localhost':
            return local

        if config.options.offline:
            print 'Error: this action is not available in offline mode'
            exit(1)

        server = config.get_section('server', server)
        host = server.options['host']
        user = self.options['user']
        return get_remote_host(host, user)



class ins_python(instance):

    class_title = u'Manage Python environments'


    def get_actions(self):
        server = self.options['server']
        if server == 'localhost':
            return ['build', 'install', 'restart', 'deploy']
        return ['build', 'upload', 'install', 'restart', 'deploy', 'test']


    def get_action(self, name):
        server = self.options['server']
        if server == 'localhost':
            if name == 'install':
                return self.action_install_local
            elif name == 'upload':
                return None
        return super(ins_python, self).get_action(name)


    def get_packages(self):
        packages = self.options['packages'].split()
        return [ x.split(':') for x in packages ]


    build_title = u'Build the source code this Python environement requires'
    def action_build(self):
        """Make a source distribution for every required Python package.
        """
        path = expanduser('~/.usine/cache')
        if not vfs.exists(path):
            vfs.make_folder(path)

        print '**********************************************************'
        print ' BUILD'
        print '**********************************************************'
        for name, branch in self.get_packages():
            config.options.branch = branch
            source = config.get_section('src_itools', name)
            source.action_dist()


    upload_title = u'Upload the source code to the remote server'
    def action_upload(self):
        """Upload every required package to the remote host.
        """
        host = self.get_host()
        print '**********************************************************'
        print ' UPLOAD'
        print '**********************************************************'
        r_path = '%s/Packages' % self.options['path']
        for name, branch in self.get_packages():
            source = config.get_section('src_itools', name)
            # Upload
            pkgname = source.get_pkgname()
            l_path = '%s/dist/%s.tar.gz' % (source.get_path(), pkgname)
            host.put(l_path, r_path)


    install_title = u'Install the source code into the Python environment'
    def action_install(self):
        """Installs every required package into the remote virtual
        environment.
        """
        host = self.get_host()
        print '**********************************************************'
        print ' INSTALL'
        print '**********************************************************'
        r_path = self.options['path']
        for name, branch in self.get_packages():
            source = config.get_section('src_itools', name)
            pkgname = source.get_pkgname()
            # Untar
            cwd = '%s/Packages' % r_path
            cmd = 'tar xzf %s.tar.gz' % pkgname
            host.run(cmd, cwd)
            # Install
            cwd = '%s/Packages/%s' % (r_path, pkgname)
            cmd = '%s/bin/python setup.py --quiet install' % r_path
            host.run(cmd, cwd)


    def action_install_local(self):
        print '**********************************************************'
        print ' INSTALL'
        print '**********************************************************'
        path = self.options['path']
        path = expanduser(path)
        command = ['%s/bin/python' % path, 'setup.py', 'install']
        for name, branch in self.get_packages():
            source = config.get_section('src_itools', name)
            cwd = source.get_path()
            local.run(command, cwd=cwd)


    restart_title = u'Restart the ikaaro instances that use this environment'
    def action_restart(self):
        """Restarts every ikaaro instance.
        """
        print '**********************************************************'
        print ' RESTART'
        print '**********************************************************'
        for ins_ikaaro in config.get_sections_by_type('ins_ikaaro'):
            if ins_ikaaro.options['ins_python'] == self.name:
                ins_ikaaro.stop()
                ins_ikaaro.start()


    deploy_title = u'All of the above'
    def action_deploy(self):
        """Deploy (build, upload, install, restart) the required Python
        packages in the remote virtual environment, and restart all the ikaaro
        instances.
        """
        actions = ['build', 'upload', 'install', 'restart']
        for name in actions:
            action = self.get_action(name)
            if action:
                action()


    test_title = (
        u'Test if ikaaro instances of this Python environment are alive')
    def action_test(self):
        """ Test if ikaaro instances of this Python environment are alive"""
        print '**********************************************************'
        print ' TEST'
        print '**********************************************************'
        for ins_ikaaro in config.get_sections_by_type('ins_ikaaro'):
            if ins_ikaaro.options['ins_python'] == self.name:
                uri = ins_ikaaro.options['uri']
                conn = HTTPConnection(uri)
                conn.request("HEAD", "/")
                res = conn.getresponse()
                print res.status, res.reason, '=>', uri



class ins_ikaaro(instance):

    class_title = u'Manage Ikaaro instances'
    class_actions = freeze(['start', 'stop', 'restart'])


    def get_host(self):
        ins_python = self.options['ins_python']
        ins_python = config.get_section('ins_python', ins_python)
        host = ins_python.get_host()
        cwd = ins_python.options['path']
        host.chdir(cwd)
        return host


    def stop(self):
        path = self.options['path']
        host = self.get_host()
        host.run('./bin/icms-stop.py %s' % path)
        host.run('./bin/icms-stop.py --force %s' % path)


    def start(self):
        cmd = './bin/icms-start.py -d %s' % self.options['path']
        host = self.get_host()
        host.run(cmd)


    start_title = u'Start an ikaaro instance'
    def action_start(self):
        print '**********************************************************'
        print ' START'
        print '**********************************************************'
        self.start()


    stop_title = u'Stop an ikaaro instance'
    def action_stop(self):
        print '**********************************************************'
        print ' STOP'
        print '**********************************************************'
        self.stop()


    restart_title = u'(Re)Start an ikaaro instance'
    def action_restart(self):
        print '**********************************************************'
        print ' RESTART'
        print '**********************************************************'
        self.stop()
        self.start()



class ins_sphinx(instance):

    def get_actions(self):
        if config.options.offline:
            return ['checkout', 'html', 'pdf', 'build', 'dist']
        return ['dist', 'deploy']


    upload_title = u'Upload the tarball to the remote server'
    def action_upload(self):
        cwd = '%s/.build' % self.get_path()
        pkgname = self.get_pkgname()
        # Upload
        l_path = '%s/%s.tar.gz' % (cwd, pkgname)
        r_path = '%s/Packages' % self.options['path']
        host = self.get_host()
        host.put(l_path, r_path)


    install_title = u'Install the documentation'
    def action_install(self):
        pkgname = self.get_pkgname()

        # Unpack tarball
        r_path = self.options['path']
        cwd = '%s/Packages' % r_path
        cmd = 'tar xpf %s.tar.gz' % pkgname
        host = self.get_host()
        host.run(cmd, cwd=cwd)
        # Make symbolic link
        cmd = 'ln -sf %s/Packages/%s htdocs' % (r_path, pkgname)
        host.run(cmd, cwd=r_path)


    deploy_title = 'All of above and deploy on remote host'
    def action_deploy(self):
        self.action_dist()
        self.action_upload()
        self.action_install()


# Register
register_module('ins_ikaaro', ins_ikaaro)
register_module('ins_python', ins_python)
register_module('ins_sphinx', ins_sphinx)
