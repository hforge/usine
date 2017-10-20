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
from ConfigParser import RawConfigParser
from os.path import expanduser

# Import from itools
from itools.core import freeze
from itools.log import log_info, log_fatal
from itools.fs import lfs

# Import from usine
from hosts import local
from modules import modules, register_module
from libusine.utils import logWrapper



class configuration(object):

    class_title = u'Manage configuration'
    class_actions = freeze([''])

    def __init__(self):
        self.by_type = {}            # type: [<data>, ..]
        self.by_type_and_name = {}   # (type, name): <data>

    def load(self):
        path = expanduser('~/.usine')
        if lfs.is_file(path):
            log_fatal('ERROR: %s is a file, remove it first' % path)

        # Make the user configuration file if needed
        if not lfs.exists(path):
            log_info('Making the configuration folder: {}'.format(path))
            lfs.make_folder(path)
            log_fatal('Now add the INI files within the folder')

        # Read the user configuration file
        ini = [ '%s/%s' % (path, x)
                for x in lfs.get_names(path) if x[-4:] == '.ini' ]
        if len(ini) == 0:
            log_fatal('ERROR: zero INI files found in {}/'.format(path))

        # Read the ini file
        cfg = RawConfigParser()
        cfg.read(ini)

        # Get the data
        for section in cfg._sections:
            options = cfg._sections[section]
            type, name = section.split()
            module = modules[type]
            obj = module(options)

            # Keep the data unit
            self.by_type.setdefault(type, []).append(obj)
            self.by_type_and_name[(type, name)] = obj

        # Sort
        for type in self.by_type:
            self.by_type[type].sort(key=lambda x: x.name)


    update_title = u'Update usine configuration'
    @logWrapper
    def action_update(self):
        """
        If config folder is a GIT repository, rebase it
        """
        path = expanduser('~/.usine')
        for x in lfs.get_names(path):
            folder = '{}/{}'.format(path, x)
            if lfs.exists('{}/.git'.format(folder)):
                local.run(['git', 'fetch', 'origin'], cwd=folder)
                local.run(['git', 'reset', '--hard', 'origin/master'], cwd=folder)


    def get_sections_by_type(self, type):
        return self.by_type.get(type, [])



    def get_sections_by_package(self, package):
        sections_packages = []
        instances = self.by_type.get('ikaaro', [])
        for instance in instances:
            pyenv = instance.options['pyenv']
            section = self.get_section('pyenv', pyenv)
            if section is None:
                continue
            packages = section.options['packages']
            if package in packages:
                sections_packages.append(instance)
        # OK
        return sections_packages



    def get_section(self, type, name):
        key = (type, name)
        return self.by_type_and_name.get(key)


# singleton
config = configuration()
register_module('config', configuration)
