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

import os
import pytest
import shutil

from flexmock import flexmock
from pathlib import Path

from container_workflow_tool.cli import ImageRebuilder
from container_workflow_tool.git_operations import GitOperations


class TestDistgit(object):
    def setup_method(self):
        self.component = 's2i-base'
        self.ir = ImageRebuilder('Testing')

        self.ir.set_config('default.yaml', release="rawhide")
        # Partner BZ testing
        self.ir.rebuild_reason = "Unit testing"
        self.ir.disable_klist = True
        self.ir.set_do_images([self.component])

    @pytest.mark.distgit
    def test_pull_downstream(self):
        tmp = Path(self.ir._get_tmp_workdir())
        self.ir.pull_downstream()
        cpath = tmp / self.component
        assert cpath.is_dir()
        dpath = cpath / 'Dockerfile'
        assert dpath.is_file()
        shutil.rmtree(tmp / self.component)

    @pytest.mark.distgit
    def test_pull_upstream(self):
        self.ir.pull_upstream()
        tmp = self.ir._get_tmp_workdir()
        cpath = os.path.join(tmp, 's2i')
        assert os.path.isdir(cpath)
        dpath = os.path.join(cpath, 'base', 'Dockerfile')
        assert os.path.isfile(dpath)

    @pytest.mark.distgit
    def test_distgit_merge_changes(self):
        self.ir.conf["from_tag"] = "test"
        tmp = Path(self.ir._get_tmp_workdir())
        self.ir.dist_git_merge_changes()
        dpath = tmp / self.component / 'Dockerfile'
        assert os.path.isfile(dpath)
        assert not (tmp / self.component / "test" / "test-openshift.yaml").exists()
        tag_found = False
        with open(dpath) as f:
            if ":test" in f.read():
                tag_found = True
        assert tag_found
        shutil.rmtree(tmp / self.component)

    @pytest.mark.distgit
    def test_distgit_merge_changes_openshift_yaml(self):
        # TODO
        # As soon as s2i-base-container will contain file 'test/test-openshift.yaml'
        # Then change it to once
        flexmock(GitOperations).should_receive("update_test_openshift_yaml").never()
        self.ir.conf["from_tag"] = "test"
        tmp = Path(self.ir._get_tmp_workdir())
        self.ir.distgit._clone_downstream(self.component, "main")
        self.ir.dist_git_merge_changes()
        dpath = tmp / self.component / 'Dockerfile'
        assert os.path.isfile(dpath)
        tag_found = False
        with open(dpath) as f:
            if ":test" in f.read():
                tag_found = True
        assert tag_found
        shutil.rmtree(tmp / self.component)

    @pytest.mark.distgit
    def test_tag_dockerfile(self):
        tmp = Path(self.ir._get_tmp_workdir())
        self.ir.conf["from_tag"] = "test"
        self.ir.dist_git_merge_changes()
        cpath = tmp / self.component
        dpath = cpath / 'Dockerfile'
        found_tag = False
        with open(dpath) as f:
            if ":test" in f.read():
                found_tag = True
        assert found_tag
        shutil.rmtree(tmp / self.component)
