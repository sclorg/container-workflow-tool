# MIT License
#
# Copyright (c) 2020 SCL team at Red Hat
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import pytest

from container_workflow_tool.cli import ImageRebuilder


class TestBrew(object):
    def setup_method(self):
        self.component = 's2i-base'
        self.ir = ImageRebuilder('Testing')

        self.ir.set_config('default.yaml', release="rawhide")
        self.ir.rebuild_reason = "Unit testing"
        self.ir.disable_klist = True
        self.ir.set_do_images([self.component])
        self.component = 'postgresql'
        self.ir.set_do_images([self.component])

    @pytest.mark.distgit
    def test_get_nvr(self):
        nvr = self.ir.brewapi.get_nvr('f26-container', self.component)
        assert nvr == 'postgresql-0-1.f26container'

    @pytest.mark.distgit
    def test_get_buildinfo(self):
        buildinfo = self.ir.brewapi.get_buildinfo('postgresql-0-1.f26container')
        assert buildinfo['build_id']
        assert buildinfo['build_id'] == 1018414

    @pytest.mark.distgit
    def test_get_taskinfo(self):
        taskinfo = self.ir.brewapi.get_taskinfo(24268996)
        assert taskinfo['create_ts']
        assert taskinfo['create_ts'] == 1516286326.921902
