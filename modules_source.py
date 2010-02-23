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
from sys import prefix
from os.path import expanduser

# Import from itools
from itools import pkg, vfs

# Import from usine
from config import config
from hosts import local
from modules import module, register_module


bin = '%s/bin' % prefix



class source(module):

    class_title = u'Manage source code'


    def get_actions(self):
        if config.options.offline:
            return ['checkout', 'build', 'dist']
        return ['sync', 'checkout', 'build', 'dist']


    def get_action(self, name):
        if config.options.offline and name == 'sync':
            return None
        return super(source, self).get_action(name)


    def get_pkgname(self):
        version = self.get_version()
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
            local.run(['git', 'branch', branch, 'origin/%s' % branch])
            local.run(['git', 'checkout', branch])
        else:
            local.run(['git', 'rebase', 'origin/%s' % branch])
        local.run('git clean -fxdq')


    sync_title = u'[private] Synchronize the source from the mirror'
    def action_sync(self):
        # Case 1: Fetch
        folder = self.get_path()
        if vfs.exists(folder):
            local.run('git fetch origin', cwd=folder)
            return

        # Case 2: Clone
        local.run(['git', 'clone', self.get_url(), folder])


    checkout_title = u'[private] Checkout the given branch (default: master)'
    def action_checkout(self):
        self._checkout(config.options.branch)


    build_title = u'[private] Build'
    def action_build(self):
        raise NotImplementedError


    dist_title = u'All of the above'
    def action_dist(self):
        actions = ['sync', 'checkout', 'build']
        for name in actions:
            action = self.get_action(name)
            if action:
                action()



class src_itools(source):

    class_title = u'Manage itools packages'

    def get_version(self):
        version = '%s/version.txt' % self.get_path()
        return open(version).read()


    def action_build(self):
        cwd = self.get_path()
        local.chdir(cwd)
        local.run(['%s/ipkg-build.py' % bin])
        local.run(['%s/python' % bin, 'setup.py', '--quiet', 'sdist'])




sphinx = (
    'sphinx-build -b {mode} -d .build/doctrees -D latex_paper_size=a4 . '
    '.build/{mode}')


class src_sphinx(source):

    converters = {
        ('png', 'png'): 'cp {source} {target}',
        ('jpg', 'png'): 'convert {source} {target}',
        ('svg', 'png'): 'inkscape -z {source} -e {target}',
        ('dot', 'png'): 'dot -Tpng {source} -o {target}',
        ('png', 'eps'): 'convert {source} -compress jpeg eps2:{target}',
        ('jpg', 'eps'):
            'convert -units PixelsPerInch -density 72 {source} eps2:{target}',
        ('svg', 'eps'): 'inkscape -z {source} -E {target}',
        ('fig', 'eps'): 'fig2dev -L eps {source} {target}',
        ('dot', 'eps'): 'dot -Tps {source} -o {target}',
    }


    def get_actions(self):
        if config.options.offline:
            return ['checkout', 'html', 'pdf', 'build', 'dist']
        return ['sync', 'checkout', 'html', 'pdf', 'build', 'dist']


    def get_version(self):
        cwd = self.get_path()
        return pkg.make_version(cwd=cwd)


    def make_figures(self, format):
        cwd = self.get_path()
        local.chdir(cwd)
        folder = vfs.open(cwd)
        for name in folder.get_names():
            if not folder.exists('%s/figures-src' % name):
                continue

            source_base = '%s/figures-src' % name
            target_base = '%s/figures' % name
            if not folder.exists(target_base):
                folder.make_folder(target_base)

            for name in folder.get_names(source_base):
                source = '%s/%s' % (source_base, name)
                mtime = folder.get_mtime(source)
                name, extension = name.rsplit('.')
                target = '%s/%s.%s' % (target_base, name, format)
                if folder.exists(target) and folder.get_mtime(target) > mtime:
                    continue
                command = self.converters.get((extension, format))
                if command:
                    command = command.format(source=source, target=target)
                    local.run(command)


    html_title = u'Make HTML'
    def action_html(self):
        # Figures
        self.make_figures('png')
        # HTML
        cwd = self.get_path()
        command = sphinx.format(mode='html')
        local.run(command, cwd=cwd)
        # Ok
        print 'Build finished. The HTML pages are in %s/.build/html' % cwd


    pdf_title = u'Make PDF'
    def action_pdf(self):
        # Figures
        self.make_figures('eps')
        # Latex
        cwd = self.get_path()
        command = sphinx.format(mode='latex')
        local.run(command, cwd=cwd)
        # PDF
        local.run('make all-pdf', cwd='%s/.build/latex' % cwd)
        print 'Your PDF is available in %s/.build/latex' % cwd


    build_title = u'Make tarball with HTML files'
    def action_build(self):
        self.action_html()

        cwd = '%s/.build' % self.get_path()
        pkgname = self.get_pkgname()
        # Copy to a folder with the right name
        command = ['cp', '-r', 'html', pkgname]
        local.run(command, cwd=cwd)
        # Make the tarball
        command = ['tar', 'czpf', '%s.tar.gz' % pkgname, pkgname]
        local.run(command, cwd=cwd)


# Register
register_module('src_itools', src_itools)
register_module('src_sphinx', src_sphinx)
