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
from os.path import expanduser
from time import sleep

# Import from pygobject
from glib import GError

# Import from itools
from itools.core import freeze, lazy
from itools.fs import lfs, vfs
from itools.log import log_info, log_error

# Import from usine
from config import config
from hosts import local, get_remote_host
from modules import module, register_module
from libusine.utils import logWrapper



cmd_vhosts = """
from itools.database import Catalog, get_register_fields
catalog = Catalog('./%s/catalog', get_register_fields(), read_only=True)
vhosts = list(catalog.get_unique_values('vhosts'))
vhosts.sort()
for vhost in vhosts:
    print vhost
"""

class instance(module):

    @lazy
    def location(self):
        location = self.options['location']
        if location[:10] == 'localhost:':
            # Case 1: local
            user, server, path = None, 'localhost', location[10:]
        else:
            # Case 2: remote
            user, location = location.split('@', 1)
            server, path = location.split(':', 1)
        if path[0] != '/':
            path = '~/%s' % path
        return user, server, path


    @lazy
    def bin_python(self):
        return '%s/bin/python' % self.location[2]


    @lazy
    def bin_pip(self):
        return '%s/bin/pip' % self.location[2]


    def get_host(self):
        user, server, path = self.location
        if server == 'localhost':
            return local

        if config.options.offline:
            log_error('Error: this action is not available in offline mode')
            exit(1)

        server = config.get_section('server', server)
        host = server.options['host']
        shell = bool(int(self.options.get('shell', '0')))
        return get_remote_host(host, user, shell)


    def get_source(self, name):
        source = config.get_section('pysrc', name)
        if source:
            return source

        raise ValueError, 'the source "%s" is not found' % name



class pyenv(instance):

    class_title = u'Manage Python environments'

    @lazy
    def is_local(self):
        return self.location[1] == 'localhost'


    @lazy
    def class_actions(self):
        actions = ['start', 'stop', 'restart', 'update', 'reindex',
                   'build', 'install', 'deploy', 'deploy_reindex']
        if not self.is_local:
            # Append remote actions
            actions.extend(['upload', 'test', 'vhosts'])
        return actions


    def get_packages(self):
        packages = self.options['packages'].split()
        return [ x.split(':') for x in packages ]


    def get_action(self, name):
        if name not in self.get_actions():
            # Ignore actions not specified in get_actions
            return None
        return super(pyenv, self).get_action(name)


    build_title = u'Build the source code this Python environment requires'
    @logWrapper
    def action_build(self):
        """Make a source distribution for every required Python package.
        """
        # Get .cache folder
        path = expanduser('~/.usine/cache')
        if not lfs.exists(path):
            lfs.make_folder(path)

        for name, version in self.get_packages():
            config.options.version = version
            source = self.get_source(name)
            if self.is_local:
                source.action_sync()
                source.action_checkout()
            else:
                # If we build for remote we want to build a dist
                source.action_dist()


    upload_title = u'Upload the source code to the remote server'
    @logWrapper
    def action_upload(self):
        """Upload every required package to the remote host.
        """
        host = self.get_host()
        for name, version in self.get_packages():
            source = self.get_source(name)
            # Upload
            pkgname = source.get_pkgname()
            l_path = '%s/dist/%s.tar.gz' % (source.get_path(), pkgname)
            host.put(l_path, '/tmp')


    install_title = u'Install the source code into the Python environment'
    @logWrapper
    def action_install(self):
        """Installs every required package (and dependencies) into the remote virtual
        environment.
        """
        # Get host
        host = self.get_host()
        # Build commands
        bin_python = expanduser(self.bin_python)
        install_command = '%s setup.py --quiet install --force' % bin_python
        pip_install_command = '%s install -r requirements.txt --upgrade' % self.bin_pip
        prefix = self.options.get('prefix')
        if prefix:
            pip_install_command += ' --prefix=%s' % prefix
            install_command += ' --prefix=%s' % prefix

        # Get package install paths
        paths = {}
        for name, version in self.get_packages():
            source = self.get_source(name)
            if self.is_local:
                source_path = source.get_path()
                paths[name] = source_path
            else:
                # If remove we need to untar sources
                log_info('UNTAR sources for {}'.format(name))
                source = self.get_source(name)
                pkgname = source.get_pkgname()
                host.run('tar xzf %s.tar.gz' % pkgname, '/tmp')
                source_path = '/tmp/%s' % pkgname
                paths[name] = source_path

        # Install
        for name, path in paths.iteritems():
            try:
                log_info('INSTALL DEPENDENCIES for {}'.format(name))
                host.run(pip_install_command, path)
            except EnvironmentError:
                # In case there is no requirements.txt
                log_info('No file requirements.txt found, ignore')
                pass
            # Install
                log_info('INSTALL package {}'.format(name))
            host.run(install_command, path)

            if not self.is_local:
                # Clean untar sources
                log_info('DELETE untar sources {}'.format(path))
                host.run('rm -rf %s' % path, '/tmp')


    restart_title = u'Restart the ikaaro instances that use this environment'
    @logWrapper
    def action_restart(self):
        """Restarts every ikaaro instance.
        """
        for ikaaro in config.get_sections_by_type('ikaaro'):
            if ikaaro.options['pyenv'] == self.name:
                ikaaro.stop()
                ikaaro.start()


    reindex_title = u'Reindex the ikaaro instances that use this environment'
    @logWrapper
    def action_reindex(self):
        """Reindex every ikaaro instance.
        """
        for ikaaro in config.get_sections_by_type('ikaaro'):
            if ikaaro.options['pyenv'] == self.name:
                ikaaro.stop()
                ikaaro.update_catalog()
                ikaaro.start()


    deploy_title = u'All of the above'
    @logWrapper
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


    deploy_reindex_title = (
        u'Build, upload, install, reindex and start the ikaaro instances')
    @logWrapper
    def action_deploy_reindex(self):
        """
        Build, upload, install the required Python packages
        in the remote virtual environment and stop, reindex and start all the
        ikaaro instances.
        """
        actions = ['build', 'upload', 'install', 'stop', 'reindex', 'start']
        for name in actions:
            action = self.get_action(name)
            if action:
                action()


    update_title = (u'Launch update methods on the ikaaro '
                    u'instances that use this environment')
    @logWrapper
    def action_update(self):
        """
        Launch update methods on every ikaaro instance.
        """
        for ikaaro in config.get_sections_by_type('ikaaro'):
            if ikaaro.options['pyenv'] == self.name:
                try:
                    ikaaro.update()
                except EnvironmentError as e:
                    log_error('[ERROR] ' + str(e))


    start_title = (
        u'Start the ikaaro instances')
    @logWrapper
    def action_start(self):
        """
        Start all the ikaaro instances.
        """
        for ikaaro in config.get_sections_by_type('ikaaro'):
            if ikaaro.options['pyenv'] == self.name:
                ikaaro.start()


    stop_title = (
        u'Stop the ikaaro instances')
    @logWrapper
    def action_stop(self):
        """
        Stop all the ikaaro instances.
        """
        for ikaaro in config.get_sections_by_type('ikaaro'):
            if ikaaro.options['pyenv'] == self.name:
                ikaaro.stop()


    test_title = (
        u'Test if ikaaro instances of this Python environment are alive')
    @logWrapper
    def action_test(self):
        """ Test if ikaaro instances of this Python environment are alive"""
        for ikaaro in config.get_sections_by_type('ikaaro'):
            if ikaaro.options['pyenv'] == self.name:
                uri = ikaaro.options['uri']
                for i in range(1, 6):
                    try:
                        vfs.open('{}/;_ctrl'.format(uri))
                    except GError:
                        log_error('[ERROR {}/5] {}'.format(i, uri))
                        sleep(0.5)
                    else:
                        log_info('[OK] {}'.format(uri))
                        break


    vhosts_title = (
        u'List vhosts of all ikaaro instances of this Python environment')
    @logWrapper
    def action_vhosts(self):
        """List vhosts of all ikaaro instances of this Python environment"""
        for ikaaro in config.get_sections_by_type('ikaaro'):
            if ikaaro.options['pyenv'] == self.name:
                ikaaro.vhosts()



class ikaaro(instance):

    class_title = u'Manage Ikaaro instances'
    class_actions = freeze([
        'start', 'stop', 'restart', 'reindex', 'update', 'vhosts'])


    @lazy
    def pyenv(self):
        pyenv = self.options['pyenv']
        return config.get_section('pyenv', pyenv)


    @lazy
    def bin_icms(self):
        pyenv = self.pyenv
        prefix = pyenv.options.get('prefix') or pyenv.location[2]
        return '%s/bin' % prefix


    def get_host(self):
        pyenv = self.pyenv
        host = pyenv.get_host()
        cwd = pyenv.location[2]
        host.chdir(cwd)
        return host


    def stop(self):
        path = self.options['path']
        host = self.get_host()
        host.run('%s/icms-stop.py %s' % (self.bin_icms, path))
        host.run('%s/icms-stop.py --force %s' % (self.bin_icms, path))


    def start(self, readonly=False):
        path = self.options['path']
        cmd = '%s/icms-start.py -d %s' % (self.bin_icms, path)
        readonly = readonly or self.options.get('readonly', False)
        if readonly:
            cmd = cmd + ' -r'
        host = self.get_host()
        host.run(cmd)


    def update_catalog(self):
        path = self.options['path']
        cmd = '{0}/icms-update-catalog.py -y {1} --quiet'.format(self.bin_icms, path)
        host = self.get_host()
        host.run(cmd)


    def update(self):
        path = self.options['path']
        cmd = '{0}/icms-update.py {1}'.format(self.bin_icms, path)
        host = self.get_host()
        host.run(cmd)


    def vhosts(self):
        path = self.options['path']
        host = self.get_host()
        cmd = cmd_vhosts % path
        host.run('./bin/python -c "%s"' % cmd, quiet=True)


    start_title = u'Start an ikaaro instance'
    @logWrapper
    def action_start(self):
        self.start()


    stop_title = u'Stop an ikaaro instance'
    @logWrapper
    def action_stop(self):
        self.stop()


    restart_title = u'(Re)Start an ikaaro instance'
    @logWrapper
    def action_restart(self):
        self.stop()
        self.start()


    reindex_title = u'Update catalog of an ikaaro instance'
    @logWrapper
    def action_reindex(self):
        self.stop()
        self.update_catalog()
        self.start()


    update_title = u'Launch update methods of an ikaaro instance'
    @logWrapper
    def action_update(self):
        self.stop()
        self.update()
        self.start()


    vhosts_title = u'List vhosts of ikaaro instance'
    @logWrapper
    def action_vhosts(self):
        self.vhosts()



# Register
register_module('ikaaro', ikaaro)
register_module('pyenv', pyenv)
