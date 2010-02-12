#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (C) 2009 Juan David Ibáñez Palomar <jdavid@itaapy.com>
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
from optparse import OptionParser, IndentedHelpFormatter
from sys import exit

# Import from usine
from libusine import config, modules, remote_hosts



class HelpFormatter(IndentedHelpFormatter):

    def format_description(self, description):
        lines = [
            u'Modules:\n',
            u'\n']
        for name in sorted(modules):
            module = modules[name]
            if module.class_title:
                lines.append(u'  %s: %s\n' % (name, module.class_title))

        return ''.join(lines)



if __name__ == '__main__':
    # Command line
    usage = 'usine.py [options] <module> <item> <action>...'
    parser = OptionParser(usage, description='foo', formatter=HelpFormatter())
    parser.add_option('--offline', action='store_true',
        help='In this mode the source code will not be syncrhonized from the '
             'mirror, and remote actions will be disabled.')
    parser.add_option('-b', '--branch', default='master',
        help='The branch to use (default: master), this option only applies '
             ' to some actions.')
    options, args = parser.parse_args()

    # Configuration
    error = config.load()
    if error:
        print error
        exit(1)
    config.options = options

    # Case 0: Nothing, print help
    if not args:
        print 'Usage:', usage
        print
        print 'Modules:'
        print
        for name in sorted(modules):
            module = modules[name]
            if module.class_title:
                print u'  %s: %s' % (name, module.class_title)
        exit(0)

    # Get the module
    module_name, args = args[0], args[1:]
    module = modules.get(module_name)
    if not module or not module.class_title:
        print 'Error: unexpected "%s" module' % module_name
        exit(1)

    # Case 1: Just the module, print help
    if not args:
        usage = 'usine.py [options] %s <item> <action>...'
        print 'Usage:', usage % module_name
        print
        print 'Items:'
        print
        for item in config.get_sections_by_type(module_name):
            print '  %s' % item.name
        exit(0)

    # Get the item
    item_name, args = args[0], args[1:]
    item = config.get_section(module_name, item_name)
    if not item:
        print 'Error: "%s" module got unexpected "%s" item' \
                % (module_name, item_name)
        exit(1)

    # Case 2: The module and the item, print help
    if not args:
        usage = 'usine.py [options] %s %s <action>...'
        print 'Usage:', usage % (module_name, item_name)
        print
        print 'Actions:'
        print
        for action in item.get_actions():
            title = getattr(module, '%s_title' % action)
            action = action + " " * (9 - len(action))
            print '  %s: %s' % (action, title)
        exit(0)

    # Case 3: The module, the item and the action(s)
    for action_name in args:
        # Get the action
        if action_name not in item.get_actions():
            print 'Error: "%s" module got unexpected "%s" action' \
                    % (module_name, action_name)
            exit(1)

        # Call
        action = item.get_action(action_name)
        action()

    # Close connections
    for host in remote_hosts.values():
        host.close()

