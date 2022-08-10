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


from container_workflow_tool.utility import RebuilderError
from container_workflow_tool.cli import ImageRebuilder


class TestRebuilder(object):
    def setup_method(self):
        self.component = 's2i-base'
        self.ir = ImageRebuilder('Testing')

        self.ir.set_config('default.yaml', release="rawhide")
        # Partner BZ testing
        self.ir.rebuild_reason = "Unit testing"
        self.ir.disable_klist = True
        self.ir.set_do_images([self.component])
        self.component = "postgresql"

    def teardown_method(self):
        self.ir.clear_cache()

    def test_set_config(self):
        self.ir.set_config("f34.yaml", release="fedora34")
        assert self.ir.conf.releases["fedora"]["current"] == "34"

    def test_do_images(self):
        self.ir.set_do_images("s2i-base")
        images = [i["component"] for i in self.ir._get_images()]
        assert "s2i-base" in images
        assert "nginx" not in images

    def test_setup_tmp_workdir(self):
        self.ir.tmp_workdir = self.ir._get_tmp_workdir()
        assert self.ir.tmp_workdir is not None
        assert "Testing" in self.ir.tmp_workdir

    def test_get_existing_tmp_workdir(self):
        tmp = self.ir._get_tmp_workdir()
        tmp2 = self.ir._get_tmp_workdir()
        assert tmp == tmp2
        self.ir.tmp_workdir = tmp

    def test_set_workdir(self):
        with pytest.raises(RebuilderError):
            self.ir.set_tmp_workdir("/tmp/nonexisting")
        tmp_path = "/tmp"
        self.ir.set_tmp_workdir(tmp_path)
        assert self.ir.tmp_workdir == tmp_path
        # Do not delete /tmp
        self.ir.tmp_workdir = None

    def test_get_set_workdir(self):
        tmp_path = "/tmp"
        self.ir.set_tmp_workdir(tmp_path)
        tmp = self.ir._get_tmp_workdir()
        assert tmp == tmp_path
        # Do not delete /tmp
        self.ir.tmp_workdir = None

    def test_set_repo_url(self):
        url = "url"
        self.ir.set_repo_url(url)
        assert self.ir.repo_url == url


class TestRebuilderNoBaseImage(object):

    def setup_method(self):
        self.component = 's2i-base'
        self.ir = ImageRebuilder('Testing')
        self.ir.base_image = None
        self.ir.set_config('default.yaml', release="rawhide")
        # Partner BZ testing
        self.ir.rebuild_reason = "Unit testing"
        self.ir.disable_klist = True
        self.ir.set_do_images([self.component])

    def test_distgit_pull_upstream(self):
        with pytest.raises(RebuilderError):
            self.ir.pull_downstream()

    def test_prebuild_check(self):
        with pytest.raises(RebuilderError):
            self.ir._prebuild_check([self.component])

    def test_main_build_images(self):
        with pytest.raises(RebuilderError):
            self.ir._build_images([self.component], branches=["rawhide"])

    def test_main_pull_downstream(self):
        with pytest.raises(RebuilderError):
            self.ir.pull_downstream()

    def test_main_pull_upstream(self):
        with pytest.raises(RebuilderError):
            self.ir.pull_upstream()

    def test_main_push_changes(self):
        with pytest.raises(RebuilderError):
            self.ir.push_changes()

    def test_main_merge_future_branches(self):
        with pytest.raises(RebuilderError):
            self.ir.merge_future_branches()

    def test_main_show_git_changes(self):
        with pytest.raises(RebuilderError):
            self.ir.show_git_changes()


class TestRebuilderNoSetupDir(object):

    def setup_method(self):
        self.component = 's2i-base'
        self.ir = ImageRebuilder('Testing')

        self.ir.set_config('default.yaml', release="rawhide")
        # Partner BZ testing
        self.ir.rebuild_reason = "Unit testing"
        self.ir.disable_klist = True
        self.ir.set_do_images([self.component])
        self.component = "postgresql"

    def test_do_not_setup_workdir(self):
        self.ir.tmp_workdir = self.ir._get_tmp_workdir(setup_dir=False)
        assert self.ir.tmp_workdir is None
