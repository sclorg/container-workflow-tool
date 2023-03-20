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
from pathlib import Path

from flexmock import flexmock

from container_workflow_tool.cli import ImageRebuilder
from tests.spellbook import DATA_DIR
from tests.conftest import get_tmp_workdir


class TestGitOperations:

    def setup_method(self):
        self.component = 's2i-base'
        self.ir = ImageRebuilder('Testing')

        self.ir.set_config('default.yaml', release="rawhide")
        # Partner BZ testing
        self.ir.rebuild_reason = "Unit testing"
        self.ir.disable_klist = True
        self.ir.set_do_images([self.component])

    @pytest.mark.distgit
    def test_distgit_commit_msg(self):
        msg = "Unit testing"
        self.ir.set_commit_msg(msg)
        assert self.ir.distgit.commit_msg == msg

    @pytest.mark.parametrize(
        "os_name,os_name_expected,version",
        [
            ("fedora", "fedora", "base"),
            ("RHEL8", "rhel8", "1.14"),
            ("RHEL9", "rhel9", "1.14"),
            ("RHSCL", "rhel7", "14"),
            ("FOO", "fedora", "bar")
        ]
    )
    def test_update_openshift_yaml(self, os_name, os_name_expected, version):
        self.ir.conf.image_names = os_name
        tmp_dir = get_tmp_workdir()
        flexmock(ImageRebuilder).should_receive("_get_tmp_workdir").and_return(tmp_dir.name)
        file_name = "test-openshift.yaml"
        target_name = Path(tmp_dir.name) / file_name
        shutil.copy(Path(DATA_DIR) / file_name, target_name)
        self.ir.git_ops.update_test_openshift_yaml(str(target_name), version=version)
        with open(target_name) as f:
            content = f.read()
        assert f"VERSION: \"{version}\"" in content
        assert f"OS: \"{os_name_expected}\"" in content
        tmp_dir.cleanup()

    @pytest.mark.parametrize(
        "tag,tag_str,variable,expected",
        [
            ("VERSION", "VERSION_NUMBER", "base", True),
            ("VERSION", "VERSION_NUMBER", "1.14", True),
            ("VERSION", "\"VERSION_NUMBER\"", "1.14", False),
            ("OS", "OS_NUMBER", "rhel8", True),
            ("VER", "VERSION_NUMBER", "base", False),
            ("OS", "OS_NUMBER", "rhel9", True),
            ("OS", "\"OS_NUMBER\"", "rhel9", False),
            ("OS", "VERSION_NUMBER", "base", False),
            ("VERSION", "VERSIONS_NUMBER", "1.14", False),
            ("SHORT_NAME", "CONTAINER_NAME", "nodejs", True),
            ("SHORT_NAME", "\"CONTAINER_NAME\"", "nodejs", False),
            ("SHORT_NAME", "CONT_NAME", "nodejs", False),
            ("SHORTNAME", "CONTAINER_NAME", "nodejs", False),
        ]
    )
    def test_update_variable_in_string(self, tag, tag_str, variable, expected):
        with open(os.path.join(DATA_DIR, "test-openshift.yaml")) as f:
            yaml_file = f.read()
        fixed = self.ir.git_ops.update_variable_in_string(fdata=yaml_file, tag=tag, tag_str=tag_str, variable=variable)
        result = f"{tag}: \"{variable}\"" in fixed
        assert result == expected
