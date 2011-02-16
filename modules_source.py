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
from itools import pkg
from itools.fs import lfs

# Import from usine
from config import config
from hosts import local
from modules import module, register_module


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
        version = local.run([executable, 'setup.py', '--version'])
        version = version.splitlines()[-1].strip()
        return '%s-%s' % (self.name.split('/')[0], version)


    def get_path(self):
        path = '~/.usine/cache/%s' % self.name.replace('/', '-')
        return expanduser(path)


    def get_url(self):
        mirror = self.options['mirror']
        mirror = config.get_section('mirror', mirror)
        mirror = mirror.options['url']
        return '%s%s.git' % (mirror, self.name)


    def _checkout(self, branch):
        cwd = self.get_path()
        local.chdir(cwd)
        try:
            local.run(['git', 'checkout', branch])
        except EnvironmentError:
            local.run(['git', 'checkout', '-b', branch, 'origin/%s' % branch])
        else:
            local.run(['git', 'reset', '--hard', 'origin/%s' % branch])
        local.run('git clean -fxdq')


    sync_title = u'[private] Synchronize the source from the mirror'
    def action_sync(self):
        # Case 1: Fetch
        folder = self.get_path()
        if lfs.exists(folder):
            local.run('git fetch origin', cwd=folder)
            return

        # Case 2: Clone
        local.run(['git', 'clone', self.get_url(), folder])


    checkout_title = u'[private] Checkout the given branch (default: master)'
    def action_checkout(self):
        self._checkout(config.options.branch)


    build_title = u'[private] Build'
    def action_build(self):
        cwd = self.get_path()
        local.chdir(cwd)
        # itools package: build
        if lfs.exists('%s/setup.conf' % cwd):
            local.run(['%s/bin/ipkg-build.py' % prefix])
        local.run([executable, 'setup.py', '--quiet', 'sdist'])


    dist_title = u'All of the above'
    def action_dist(self):
        actions = ['sync', 'checkout', 'build']
        for name in actions:
            action = self.get_action(name)
            if action:
                action()


# Register
register_module('pysrc', pysrc)
