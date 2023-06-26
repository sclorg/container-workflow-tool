import sys
import os

from container_workflow_tool.utility import ArgParser
from container_workflow_tool.constants import actions


class CliCommon(object):

    prg_name = None

    def __init__(self, iargs=None):
        if iargs:
            self.args = self.get_parser().parse_args(iargs)

    def parse_args(self, iargs):
        return self.get_parser().parse_args(iargs)

    def get_parser(self):
        self.prg_name = os.path.basename(sys.argv[0])
        parser = ArgParser(usage=self.cli_usage())
        parser.add_argument('-v, --verbosity', default=4, type=int, choices=range(1, 6), dest="verbosity")
        parser.add_argument('--config',
                            help='Overrides default configuration file, expects the name of file a inside the config folder without .yml, ie rhscl230')
        parser.add_argument('--tmp', help='Overrides default temporary working directory')
        parser.add_argument('--clear-cache', action='store_true', help='Clears tmp dir before running the command')
        parser.add_argument('--latest-release', action='store_true',
                            help='Work with latest brew builds by release value')
        parser.add_argument('--do-image',
                            help='Use a custom set of images instead of all from the config (use dist-git names)',
                            action='append')
        parser.add_argument('--exclude-image',
                            help='Exclude an image from the list of images defined by config (use dist-git names)',
                            action='append')
        parser.add_argument('--do-set',
                            help='Use a specific set of images instead of all from the config (use dist-git names)',
                            action='append')
        parser.add_argument('--disable-klist', action='store_true',
                            help='Disables getting kerberos token by klist')
        parser.add_argument('--output-file',
                            help='Specify output file, where some actions stores computer readable results')
        parser.add_argument('--base', nargs='?')
        subparsers = parser.add_subparsers(dest='command')
        subparsers.required = True

        # Setup a subparser for each command
        parsers = {}
        for command in actions:
            usage = getattr(self, command + '_usage')
            p = subparsers.add_parser(command, usage=usage())
            p.add_argument('action', choices=actions[command])
            parsers[command] = p

        # Setup a general build subparser
        usage = self.build_usage
        p = subparsers.add_parser('build', usage=usage())
        p.add_argument('image_set')
        parsers['build'] = p
        parsers['git'].add_argument('--rebuild-reason', help='Use a custom reason for rebuilding')
        parsers['git'].add_argument('--commit-msg', help='Use a custom message instead of the default one')
        parsers['git'].add_argument('--check-script', help='Script/command to be run when checking repositories')
        parsers['build'].add_argument(
            '--repo-url', help='Set the url of a .repo file to be used when building the image'
        )
        return parser

    def cli_usage(self):
        action_help = """{prg} [options] command
    Command:
        {cmd}
        build           - Command for building images
        git             - Work with upstream/downstream git repositories
        utils           - Other actions tied to the rebuild (communication, repository preparation etc.)

    Options:
        -v, --verbosity      - Verbosity level, 1 (Critical only) - 5 (Debug messages), default 4 (Info)
        --base               - Specific base image release, required for some actions
        --clear-cache        - Clears tmp dir before running the command
        --latest-release     - Work with latest brew builds by release value
        --config             - Overrides default configuration file,
                               expects the name of file a inside the config folder, optionally takes image_set argument
                               example usage: --config default.yaml:fedora27
        --do-image           - Use a custom set of images instead of all from the config (use dist-git names)
        --exclude-image      - Exclude an image from the list of images defined by config (use dist-git names)
        --do-set             - Use a specific set of images instead of all from the config (use dist-git names)
        --tmp                - Overrides default temporary working directory
        --disable-klist      - Disables getting kerberos token by klist
        --output-file        - Save output of cwt into a output_file
        {args}
"""
        return action_help

    def git_usage(self):
        action_help = """%s git action [options]
    Action:%s
        merge            - Clone dist-git, merges content from primary branch to future branches
        cloneupstream    - Clones upstream git repositories
        clonedownstream  - Pulls downstream dist-git repositories and does not make any further changes to them
        pullupstream     - Clone dist-git, clone upstream, copy content from upstream repo to dist-git,
                           commit (all images; does not push, manual review/push needed)
        push             - Pushes local changes for all components into downstream dist-git repository
        rebase           - Clone dist-git, bump release, commit, push, build in brew
        show             - Walk trough git repositories and show changes for each

    Options:
        --commit-msg     - Use a custom message instead of the default one
        --rebuild-reason - Use a custom reason for rebuilding
        --check-script   - Script/command to be run when checking repositories
    """
        return action_help

    def koji_usage(self):
        action_help = """%s koji action
    Action:%s
        latestbuilds - Query koji and list latest builds of images
    """
        return action_help

    def build_usage(self):
        action_help = """%s build image_set
    image_set       - ID of the image set to be built. Sets can be defined in the config file
    Options:
        --repo-url  - Set the url of a .repo file to be used when building the image
    """
        return action_help % self.prg_name

    def utils_usage(self):
        action_help = """%s utils action
    Action:%s
        listimages   - List all images (names in repo without namespace) that we work with
        listupstream - Print information about images' upstream repository
        showconfig   - Print the contents of the configuration file used
    """
        return action_help
