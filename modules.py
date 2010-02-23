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
from sys import exit

# Import from itools
from itools.core import freeze


class module(object):

    class_title = None
    class_actions = freeze([])

    def __init__(self, options):
        self.name = options['__name__'].split()[1]
        self.options = options.copy()


    def get_actions(self):
        return self.class_actions


    def get_action(self, name):
        return getattr(self, 'action_%s' % name, None)



class server(module):
    pass



class mirror(module):
    pass



# Registry
modules = {}


def register_module(name, module):
    modules[name] = module


register_module('mirror', mirror)
register_module('server', server)
