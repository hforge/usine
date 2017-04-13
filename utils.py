# -*- coding: UTF-8 -*-
# Copyright (C) 2017 Florent Chenebault <florent.chenebault@gmail.com>
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

# Import from standard
from _socket import gethostname
from datetime import datetime
from sys import stderr

# Import from itools
from time import strftime

from itools.log import log_info, Logger


def logWrapper(func):
    """Decorator used to log start and end of functions"""
    def wrapper(*args, **kwargs):
        # Remove action in the function name
        func_name = func.__name__.split('action_')[1]
        start_dtime = datetime.now()
        log_info('Start {} ({})'.format(func_name, start_dtime))
        # Function call !
        func(*args, **kwargs)
        duration = datetime.now() - start_dtime
        log_info('End {} (duration : {})'.format(func_name, duration))
    return wrapper



class UsineLogger(Logger):
    """
    Override default logger to always write to stderr !
    """

    def log(self, domain, level, message):
        """Override to always write to stdout"""
        # Add carriage return for print message
        print_msg = message + '\n'
        stderr.write(print_msg)
        # Override to always write to stdout !
        super(UsineLogger, self).log(domain, level, message)


    def format(self, domain, level, message):
        """Override to not log traceback"""
        date = strftime('%Y-%m-%d %H:%M:%S')
        host = gethostname()
        header = '{0} {1}: {2}\n'
        return header.format(date, host, message)
