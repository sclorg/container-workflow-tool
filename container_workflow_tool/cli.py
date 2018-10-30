import sys
import os

from container_workflow_tool.main import ImageRebuilder, RebuilderError
from container_workflow_tool.constants import action_map
from container_workflow_tool.cli_common import CliCommon


class Cli(CliCommon):

    def __init__(self, iargs=None):
        if iargs is not None:
            self.prg_name = os.path.basename(sys.argv[0])
            self.args = self.get_parser().parse_args(iargs)
            self.rebuilder = ImageRebuilder.from_args(self.args)

    def cli_usage(self):
        return CliCommon.cli_usage(self).format(prg=self.prg_name,
                                                cmd="koji            - List builds, base images, hash ids",
                                                args="")

    def utils_usage(self):
        return CliCommon.utils_usage(self) % (self.prg_name, "")

    def koji_usage(self):
        return CliCommon.koji_usage(self) % (self.prg_name, "")

    def git_usage(self):
        return CliCommon.git_usage(self) % (self.prg_name, "")

    def run(self):
        if self.args.command == "build":
            method_name = "build_images"
        else:
            method_name = action_map[self.args.command][self.args.action]
        run_function = getattr(self.rebuilder, method_name)
        run_function()


def run():
    try:
        cli = Cli(sys.argv[1:])
        cli.run()
    except RebuilderError as e:
        print("ERROR: {}".format(e))
        sys.exit(1)
