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

from flexmock import flexmock

from container_workflow_tool.cli import ImageRebuilder
from container_workflow_tool.koji import KojiAPI


class TestRebuilderPrinter(object):
    def setup_method(self):
        self.cwd = os.getcwd()
        self.component = "s2i-base"
        self.ir = ImageRebuilder("Testing")

        self.ir.set_config("f34.yaml", release="fedora34")
        # Partner BZ testing
        self.ir.rebuild_reason = "Unit testing"
        self.ir.disable_klist = True
        self.ir.set_do_images([self.component])

    def test_config_contents(self, capsys):
        self.ir.show_config_contents()
        output, error = capsys.readouterr()
        assert "python3" in output

    def test_latestbuilds(self, brewapi_get_nvrs, brewapi_get_buildinfo_s2i_base, brewapi_get_buildinfo_s2i_core,
                          brewapi_get_buildinfo_python3, brewapi_list_archives_s2i_base,
                          brewapi_list_archives_s2i_core, brewapi_list_archives_python3):
        flexmock(KojiAPI).should_receive("get_nvrs").and_return(brewapi_get_nvrs)
        flexmock(KojiAPI).should_receive("get_buildinfo").\
            with_args("s2i-core-0-51.container").\
            and_return(brewapi_get_buildinfo_s2i_core)
        flexmock(KojiAPI).should_receive("get_buildinfo").\
            with_args("s2i-base-1-63.container").\
            and_return(brewapi_get_buildinfo_s2i_base)
        flexmock(KojiAPI).should_receive("get_buildinfo").\
            with_args("python3-0-31.container").\
            and_return(brewapi_get_buildinfo_python3)
        flexmock(KojiAPI).should_receive("get_listarchives").\
            with_args(brewapi_get_buildinfo_s2i_core["build_id"]).\
            and_return([brewapi_list_archives_s2i_core])
        flexmock(KojiAPI).should_receive("get_listarchives").\
            with_args(brewapi_get_buildinfo_s2i_base["build_id"]).\
            and_return([brewapi_list_archives_s2i_base])
        flexmock(KojiAPI).should_receive("get_listarchives").\
            with_args(brewapi_get_buildinfo_python3["build_id"]).\
            and_return([brewapi_list_archives_python3])
        self.ir = ImageRebuilder("Testing")
        self.ir.set_config("f34.yaml", release="fedora34")
        output = self.ir.get_brew_builds(print_time=False)
        expected_output = [
            "||Component||Build||Image_name||Archives||",
            "|s2i-core|s2i-core-0-51.container|f34/s2i-core:0-51.container|1",
            "|s2i-base|s2i-base-1-63.container|f34/s2i-base:1-63.container|1",
            "|python3|python3-0-31.container|f34/python3:0-31.container|1"
        ]
        assert output == expected_output
