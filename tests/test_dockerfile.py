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

import container_workflow_tool
from container_workflow_tool.dockerfile import DockerfileHandler


class TestDockerfile:
    def setup_method(self):
        self.dfh = DockerfileHandler(base_image="s2i-core:f37")

    @pytest.mark.parametrize(
        "fdata,expected_path",
        [
            ("FROM quay.io/fedora/s2i-core:37\nSOMETHING", "quay.io/fedora/s2i-core:37"),
            ("FROM fedora/s2i-core:37\nSOMETHING2", "fedora/s2i-core:37"),
        ]
    )
    def test_get_from(self, fdata, expected_path):
        assert self.dfh.get_from(fdata) == expected_path

    def test_wrong_get_from(self):
        fdata = "FROM \nSOMETHING"
        with pytest.raises(container_workflow_tool.utility.RebuilderError):
            self.dfh.get_from(fdata)

    @pytest.mark.parametrize(
        "fdata,from_tag,expected_path",
        [
            ("FROM quay.io/fedora/s2i-core:37\nSOMETHING",  "F37", "FROM quay.io/fedora/s2i-core:F37\nSOMETHING"),
            ("FROM fedora/s2i-core:37\nSOMETHING2", "Fedora37", "FROM fedora/s2i-core:Fedora37\nSOMETHING2"),
        ]
    )
    def test_set_from(self, fdata, from_tag, expected_path):
        assert self.dfh.set_from(fdata=fdata, from_tag=from_tag) == expected_path

    def test_set_from_wrong_get_from(self):
        fdata = "FROM \nSOMETHING"
        assert self.dfh.set_from(fdata, from_tag="dummy") == fdata
