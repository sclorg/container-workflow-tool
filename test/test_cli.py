import re
import unittest

from test.common import PrinterBase
from container_workflow_tool.constants import actions
import container_workflow_tool.cli as cli
from container_workflow_tool.cli import Cli


class CliTestCase(PrinterBase):
    def test_action_map(self):
        for command in actions:
            # Check if given action for a command maps to an existing method
            for action in list(actions[command]):
                self.assertIsNotNone(getattr(self.ir,
                                             cli.action_map[command][action],
                                             None))

    def test_usage(self):
        c = Cli(None)
        cli_usage = c.cli_usage()
        # Check if all commands are mentioned in their respective usage texts
        for command in actions:
            usage = getattr(c, command + '_usage')()
            res = bool(re.search("\n\s+" + command, cli_usage))
            self.assertTrue(res, "{} not in cli_usage".format(command))
            for action in list(actions[command]):
                res = bool(re.search("\n\s+" + action, usage))
                self.assertTrue(res, "{} not in {} usage".format(action,
                                                                 command))

        # Check if all common arguments are present in usage
        parser = c.get_parser()
        for arg in parser._actions:
            for opt in arg.option_strings:
                # Ignore help
                if opt in ['-h', '--help']:
                    continue
                res = opt in cli_usage
                self.assertTrue(res, "{} not in cli_usage". format(opt))

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
                    self.assertTrue(res, "{} not in {} usage". format(opt, sp))


if __name__ == '__main__':
    unittest.main()
