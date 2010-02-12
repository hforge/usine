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
from ConfigParser import RawConfigParser
from os.path import expanduser
from sys import stdin

# Import from itools
from itools import vfs

# Import from usine
from modules import modules



class configuration(object):

    def __init__(self):
        self.by_type = {}            # type: [<data>, ..]
        self.by_type_and_name = {}   # (type, name): <data>


    def load(self):
        path = expanduser('~/.usine')
        if vfs.is_file(path):
            return 'ERROR: %s is a file, remove it first' % path

        # Make the user configuration file if needed
        if not vfs.exists(path):
            print 'Making the configuration folder:', path
            vfs.make_folder(path)
            return 'Now add the INI files within the folder'

        # Read the user configuration file
        ini  = [ '%s/%s' % (path, x)
                 for x in vfs.get_names(path) if x[-4:] == '.ini' ]
        if len(ini) == 0:
            return 'ERROR: zero INI files found in %s/' % path

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


    def get_sections_by_type(self, type):
        return self.by_type.get(type, [])


    def get_section(self, type, name):
        key = (type, name)
        return self.by_type_and_name.get(key)


# singleton
config = configuration()
