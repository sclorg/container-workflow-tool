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

from container_workflow_tool import utility
from container_workflow_tool.cli import ImageRebuilder
from container_workflow_tool.utility import RebuilderError


class TestRebuilderUtility(object):
    def setup_method(self):
        self.component = 's2i-base'
        self.ir = ImageRebuilder('Testing')

        self.ir.set_config('default.yaml', release="rawhide")

    @pytest.mark.parametrize(
        "config,expected_path,expected_image_set",
        [
            ("fedora35.yaml", "fedora35.yaml", "current"),
            ("fedora35.yaml:f35", "fedora35.yaml", "f35"),
            ("/usr/local/cwt/config/fedora35.yaml:f35", "/usr/local/cwt/config/fedora35.yaml", "f35")
        ]
    )
    def test_split_config_path(self, config, expected_path, expected_image_set):
        path, image_set = utility._split_config_path(config=config)
        assert path == expected_path
        assert image_set == expected_image_set

    def test_split_config_path_more_args(self):
        with pytest.raises(RebuilderError):
            utility._split_config_path(config="fedora35.yaml:f35:something")

    def test_get_hostname_url(self):
        hostname = utility._get_hostname_url(self.ir.conf)
        assert hostname == "https://src.fedoraproject.org"

    def test_get_hostname_url_empty(self):
        self.ir.conf.pop("hostname_url")
        assert not utility._get_hostname_url(self.ir.conf)

    def test_get_default_packager(self):
        assert "fedpkg" == utility._get_packager(self.ir.conf)

    def test_get_user_defined_packager(self):
        self.ir.conf["packager_util"] = "foobar"
        assert "foobar" == utility._get_packager(self.ir.conf)

    def test_get_not_specified_packager(self):
        self.ir.conf.pop("packager_util")
        assert "fedpkg" == utility._get_packager(self.ir.conf)
