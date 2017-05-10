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
from sys import prefix, executable
from os.path import expanduser

# Import from itools
from itools.fs import lfs

# Import from usine
from config import config
from hosts import local
from modules import module, register_module
from utils import logWrapper


class pysrc(module):

    class_title = u'Manage Python packages'


    def get_actions(self):
        if config.options.offline:
            return ['checkout', 'build', 'dist']
        return ['sync', 'checkout', 'build', 'dist']


    def get_action(self, name):
        if config.options.offline and name == 'sync':
            return None
        return super(pysrc, self).get_action(name)


    def get_pkgname(self):
        cwd = self.get_path()
        local.chdir(cwd)
        return local.run([executable, 'setup.py', '--fullname']).strip()


    def get_path(self):
        path = '~/.usine/cache/%s' % self.name.replace('/', '-')
        return expanduser(path)


    def get_url(self):
        mirror = self.options['mirror']
        mirror = config.get_section('mirror', mirror)
        mirror = mirror.options['url']
        return '%s%s.git' % (mirror, self.name)


    def _checkout(self, version):
        cwd = self.get_path()
        local.chdir(cwd)
        on_tag = version.startswith('@')
        if not on_tag:
            # Checkout branch
            try:
                local.run(['git', 'checkout', version])
            except EnvironmentError:
                local.run(['git', 'checkout', '-b', version, 'origin/%s' % version])
            else:
                local.run(['git', 'reset', '--hard', 'origin/%s' % version])
        else:
            # Checkout tag
            tag = version[1:]
            local.run(['git', 'fetch', '--tags'])
            local.run(['git', 'checkout', tag])
        local.run('git clean -fxdq')



    sync_title = u'[private] Synchronize the source from the mirror'
    @logWrapper
    def action_sync(self):
        folder = self.get_path()
        if lfs.exists(folder):
            # Case 1: Fetch
            local.run('git fetch origin', cwd=folder)
        else:
            # Case 2: Clone
            local.run(['git', 'clone', self.get_url(), folder])
        # Update submodules
        local.run(['git', 'submodule', 'update', '--init', '--recursive'], cwd=folder)



    checkout_title = u'[private] Checkout the given branch (default: master)'
    @logWrapper
    def action_checkout(self):
        self._checkout(config.options.version)


    build_title = u'[private] Build'
    @logWrapper
    def action_build(self):
        cwd = self.get_path()
        local.chdir(cwd)
        local.run([executable, 'setup.py', '--quiet', 'sdist'])


    dist_title = u'All of the above'
    @logWrapper
    def action_dist(self):
        actions = ['sync', 'checkout', 'build']
        for name in actions:
            action = self.get_action(name)
            if action:
                action()


# Register
register_module('pysrc', pysrc)
