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
import re

import container_workflow_tool.cli as cli
from container_workflow_tool.constants import actions
from container_workflow_tool.cli import Cli, ImageRebuilder


class TestCli(object):
    def setup_method(self):
        self.component = 's2i-base'
        self.ir = ImageRebuilder('Testing')

        self.ir.set_config('default.yaml', release="rawhide")
        # Partner BZ testing
        self.ir.rebuild_reason = "Unit testing"
        self.ir.disable_klist = True
        self.ir.set_do_images([self.component])
        self.component = 'postgresql'
        self.ir.set_do_images([self.component])

    def test_action_map(self):
        for command in actions:
            for action in list(actions[command]):
                assert getattr(self.ir, cli.action_map[command][action])

    @pytest.mark.parametrize(
        "command,expected",
        [
            ("git", True),
            ("utils", True),
            ("koji", True),
        ]
    )
    def test_usage(self, command, expected):
        c = Cli(None)
        cli_usage = c.cli_usage()
        # Check if all commands are mentioned in their respective usage texts
        usage = getattr(c, command + '_usage')()
        res = bool(re.search(r"\n\s+" + command, cli_usage))
        assert res == expected
        for action in list(actions[command]):
            res = bool(re.search(r"\n\s+" + action, usage))
            assert res == expected

    def test_wrong_usage(self):
        c = Cli(None)
        # Check if all commands are mentioned in their respective usage texts
        with pytest.raises(AttributeError):
            getattr(c, "foobar_usage")

    def test_common_arguments(self):
        c = Cli(None)
        cli_usage = c.cli_usage()
        # Check if all common arguments are present in usage
        parser = c.get_parser()
        for arg in parser._actions:
            for opt in arg.option_strings:
                # Ignore help
                if opt in ['-h', '--help']:
                    continue
                res = opt in cli_usage
                assert res

    def test_command_specific_arguments(self):
        c = Cli(None)
        # Check if all common arguments are present in usage
        parser = c.get_parser()
        # Do the same for command specific arguments
        subparser = parser._subparsers._group_actions[0]
        for sp in subparser.choices:
            usage = getattr(c, sp + '_usage')()
            for arg in subparser.choices[sp]._actions:
                for opt in arg.option_strings:
                    # Ignore help
                    if opt in ['-h', '--help']:
                        continue
                    res = opt in usage
                    assert res
