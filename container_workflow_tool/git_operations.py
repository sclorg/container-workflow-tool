# MIT License
#
# Copyright (c) 2023 SCL team at Red Hat
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
import subprocess
import shutil
import re

from git import Repo
from git.exc import GitCommandError

from container_workflow_tool.utility import RebuilderError, setup_logger
from container_workflow_tool.sync import SyncHandler


class GitOperations(object):
    """Class for working with git."""

    def __init__(self, base_image, conf, rebuild_reason, logger):
        self.conf = conf
        self.base_image = base_image
        if not rebuild_reason:
            rebuild_reason = self.conf.rebuild_reason
        self.rebuild_reason = rebuild_reason.format(base_image=base_image)
        self.logger = logger if logger else setup_logger("git-ops")
        self.df_ext = self.conf.df_ext
        self.sync_handler = SyncHandler(logger=logger)
        self.commit_msg = None

    def set_commit_msg(self, msg):
        """
        Set the commit message to some other than the default one.

        Args:
            msg(str): Message to be written into the commit.
        """
        self.commit_msg = msg

    def do_git_reset(self, repo):
        file_list = ['--', '.gitignore'] + self.conf.ignore_files
        repo.git.reset(file_list)
        # One file at a time to make sure all files get reset even on error
        for f in file_list[1:]:
            repo.git.checkout('--', f, with_exceptions=False)
            self.logger.debug("Removing changes for: " + f)
            # Remove all ignored files that are also untracked
            untracked = repo.git.ls_files('-o').split('\n')
            if f in untracked:
                repo.git.clean('-xfd', f)
                self.logger.debug("Removing untracked ignored file: " + f)

    def clone_upstream(self, url, ups_path, commands=None):
        """
        :params: url is URL to repofile from upstream. https://github.com/sclorg
        :param: ups_path is path where URL is cloned locally
        :params: commands has a format mentioned in config.yaml files
         Like for ./config/rawhide.yaml file and at the varnish container
         the structure is:
         varnish:
               user: "luhliari"
               commands:
                 1: "make generate-all"
        :return: repo object
        """
        try:
            repo = Repo.clone_from(url=url, to_path=ups_path)
            self.logger.info("Cloned into: " + url)
            for submodule in repo.submodules:
                submodule.update(init=True)

        except GitCommandError:
            # Generally the directory already exists, try to open as a repo instead
            # Throws InvalidGitRepositoryError if it is not a git repo
            repo = Repo(ups_path)
            self.logger.info("Using existing repository.")

        # Run the commands either way
        self.logger.debug("Running commands in upstream repo.")
        # Need to be in the upstream git root, so change cwd
        oldcwd = os.getcwd()
        os.chdir(ups_path)
        if commands:
            for order in sorted(commands):
                cmd = commands[order]
                self.logger.debug("Running '{o}' command '{c}'".format(o=order,
                                                                       c=cmd))
                ret = subprocess.run(cmd, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, shell=True,
                                     executable='/bin/bash')
                if ret.returncode != 0:
                    msg = "'{c}' failed".format(c=cmd.split(" "))
                    self.logger.error(ret.stderr)
                    raise RebuilderError(msg)
        os.chdir(oldcwd)
        return repo

    def are_unpushed_commits_available(self, repo, branch_name="") -> bool:
        """
        Get unpushed commits
        :param repo: repo object to check for unpushed commits
        :param branch_name: In case of gitlab, branch_name has to be defined.
        :param branch_name: In case of gitlab, branch_name has to be defined.
                            branch_name is e.g. rhel-8.7.0 and 'repo.active_branch.name' is 'rhel-8.7.0-<ubi_name>'
        :return: List of commits or empty array
        """
        branch = repo.active_branch.name
        # Get a list of commits that have not been pushed to remote
        select = "origin/" + branch + ".." + branch
        if branch_name != "":
            select = "origin/" + branch_name + ".." + branch
        return bool(list(repo.iter_commits(select)))

    def show_git_changes(self, tmp, components=None, diff=False, branch_name=""):
        """Shows changes made to tracked files in local downstream repositories

        Walks through all repositories and calls 'git-show' or 'git-diff' on each of them.

        Args:
            tmp (str): Path to the directory that is used to store git repositories
            components (list of str, optional): List of components to show changes for
            diff (boolean, optional): Controls whether the method calls git-show or git-diff
            branch_name (str, optional): In case of gitlab, branch_name has to be defined.
                            branch_name is e.g. rhel-8.7.0 and 'repo.active_branch.name' is 'rhel-8.7.0-<ubi_name>'
        """
        # Function to check if a path contains a git repository
        def is_git(x): return os.path.isdir(os.path.join(x, '.git'))
        files = None
        command = 'diff' if diff else 'show'
        # Create a list of repository paths
        if not components:
            # Get the whole subdirectory
            files = [f.path for f in os.scandir(tmp) if is_git(f.path)]
        else:
            if isinstance(components, str):
                components = [components]
            files = [path for path in [os.path.join(tmp, c) for c in components] if is_git(path)]
        if not files:
            self.logger.warn("No git repositories found in directory " + tmp)
        # Walk through the repositories and show changes made in the last commit
        for path in files:
            repo = Repo(path)
            # Only show changes if there are unpushed commits to show
            # or we only want the diff of unstaged changes
            if self.are_unpushed_commits_available(repo, branch_name=branch_name) or diff:
                # Clears the screen
                print(chr(27) + "[2J")
                # Force pager for short git diffs
                subprocess.run(
                    "git config core.pager 'less -+F' --replace-all",
                    cwd=path,
                    shell=True
                )
                # Not using GitPython as its git.show seems to have some problems with encoding
                subprocess.run(['git', command], cwd=path)

    def update_variable_in_string(self, fdata: str = "", tag: str = "", tag_str: str = "", variable: str = ""):
        """
        Updates variable in string. Mainly used for updating test-openshift.yaml file.
        It replaces VERSION: VERSION_NUMBER -> VERSION: variable and
        It replaces OS: OS_VERSION -> OS: <os_name>"
        """
        ret = re.sub(rf"{tag}: {tag_str}", f"{tag}: \"{variable}\"", fdata)
        return ret

    def update_test_openshift_yaml(self, test_openshift_yaml, version: str = "", short_name: str = ""):
        """
        Update test/test-openshift.yaml file with value VERSION_NUMBER and OS_NUMBER
        The file is used for CVP pipeline
        Args:
            test_openshift_yaml (Path): Path to test/test-openshift.yaml file
            version (str): version to be replaced with VERSION_NUMBER
            short_name (str): short_name to be replaced with CONTAINER_NAME
            image_names (str): image_names specified to be replaced with OS_NUMBER
        """
        with open(test_openshift_yaml) as f:
            fdata = f.read()
        fdata = self.update_variable_in_string(fdata, "VERSION", "VERSION_NUMBER", version)
        os_name = "fedora"
        if self.conf.image_names == "RHEL8":
            os_name = "rhel8"
        elif self.conf.image_names == "RHEL9":
            os_name = "rhel9"
        elif self.conf.image_names == "RHSCL":
            os_name = "rhel7"
        fdata = self.update_variable_in_string(fdata, tag="OS", tag_str="OS_NUMBER", variable=os_name)
        fdata = self.update_variable_in_string(fdata, tag="SHORT_NAME", tag_str="CONTAINER_NAME", variable=short_name)
        with open(test_openshift_yaml, 'w') as f:
            f.write(fdata)

    def get_commit_msg(self, rebase, image=None, ups_hash=None):
        """Method to create a commit message to be used in git operations

        Returns a general commit message depending on the value of the rebase
        argument, or the user-specified commit message.

        Args:
            rebase (bool): Specify if the rebase message is created
            image (dict, optional): Metadata about the image being processed
            ups_hash (str, optional): Upstream commit hash sources were synced from

        Returns:
            str: Resulting commit message text
        """
        if self.commit_msg is not None:
            return self.commit_msg
        if rebase is True:
            commit = "Rebuild for: {}".format(self.rebuild_reason)
        elif rebase is False:
            t = "Pull changes from upstream and rebase for: {}"
            commit = t.format(self.rebuild_reason)
        else:
            t = "Unknown rebase argument provided: {}"
            raise RebuilderError(t.format(str(rebase)))
        if ups_hash:
            commit += "\n created from upstream commit: " + ups_hash
        return commit

    def pull_upstream(self, component, path, url, repo, ups_name, commands):
        """Pulls an upstream repo and copies it into downstream"""
        ups_path = os.path.join('upstreams/', ups_name)
        cp_path = os.path.join(ups_path, path)

        # First check if there is a version upstream
        # If not we just skip the whole copy action
        if not os.path.exists(cp_path):
            msg = "Source {} does not exist, skipping copy upstream."
            self.logger.warning(msg.format(cp_path))
            return

        for f in repo.git.ls_files().split('\n'):
            file = os.path.join(component, f)
            if os.path.isdir(file) and not os.path.islink(file):
                shutil.rmtree(file)
            else:
                os.remove(file)

        # No need for upstream .git files so we remove them
        shutil.rmtree(os.path.join(ups_path, path, '.git'), ignore_errors=True)
        self.sync_handler.copy_upstream2downstream(cp_path, component)
        self.sync_handler.handle_dangling_symlinks(cp_path, component)
        # If README.md exists but help.md does not, create a symlink
        help_md = os.path.join(component, "help.md")
        readme_md = os.path.join(component, "README.md")
        if not os.path.isfile(help_md):
            if os.path.isfile(readme_md):
                os.symlink("README.md", help_md)
                repo.git.add('help.md')
            else:
                # Report warning if help.md does not exists
                self.logger.warn("help.md file missing")
        # Add all the changes and remove those we do not want
        test_openshift_yaml_file = os.path.join(component, "test", "test-openshift.yaml")
        if os.path.exists(test_openshift_yaml_file):
            self.update_test_openshift_yaml(test_openshift_yaml_file, path, short_name=ups_name)

        repo.git.add("*")
        self.do_git_reset(repo)
        # TODO: Configurable?
        df_ext = self.df_ext
        df_path = os.path.join(component, "Dockerfile")
        if os.path.isfile(df_path + df_ext) and not os.path.islink(df_path + df_ext):
            try:
                os.remove(df_path)
            except FileNotFoundError:
                # We don't care whether CentOS dockerfile exists or not. Just don't fail here.
                pass
            repo.git.mv("Dockerfile" + df_ext, "Dockerfile")
            os.symlink("Dockerfile", df_path + df_ext)
            repo.git.add("Dockerfile", "Dockerfile" + df_ext)

        # Make sure a $VERSION symlink exists
        version = os.path.basename(cp_path)
        link_name = os.path.join(component, version)
        if not os.path.islink(link_name):
            try:
                os.symlink(".", link_name)
                repo.git.add(version)
            except FileExistsError:  # noqa: F821 - Doesnt see built-ins?
                t = "Failed creating symlink '{}' -> '.', file already exists."
                raise RebuilderError(t.format(link_name))

        # Run post upstream pull hook
        self._post_upstream_pull(cp_path, component)

    def _post_upstream_pull(self, upstream_path, downstream_path):
        """Post upstream pull hook"""
        pass
