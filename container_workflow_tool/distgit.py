import os
import shutil
import subprocess

from git import Repo
from git.exc import GitCommandError

from container_workflow_tool import utility
from container_workflow_tool.utility import RebuilderError
from container_workflow_tool.dockerfile import DockerfileHandler
from container_workflow_tool.sync import SyncHandler
from container_workflow_tool.git_operations import GitOperations


class DistgitAPI(GitOperations):
    """Class for working with dist-git."""

    def __init__(self, *args, **kwargs):
        super(DistgitAPI, self).__init__(*args, **kwargs)
        self.df_ext = self.conf.df_ext
        self.df_handler = DockerfileHandler(self.base_image, logger=self.logger)
        self.sync_handler = SyncHandler(logger=self.logger)

    # FIXME: This should be provided by some external Dockerfile linters
    def _check_labels(self, dockerfile_path):
        old_labels = ['Release=', 'Name=', 'Version=']
        with open(dockerfile_path) as f:
            fdata = f.read()
        for label in old_labels:
            if label in fdata:
                self.logger.warn("Wrong label '{}' found in {}".format(label, dockerfile_path))

    def check_script(self, component, script_path, component_path):
        """Method that runs a given script against given directory

        Runs the script as provided by script_path and checks its exit value.
        Prints the content of stderr when the sciprt fails (exit value != 0).

        Args:
            component (string): name of the component being checked
            script_path (string): script that should be run during the check
            component_path (string): path to the directory being checked
        """
        template = "{name}: {status}"
        ret = subprocess.run(script_path, shell=True, stderr=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, cwd=component_path)

        if ret.returncode != 0:
            self.logger.info(template.format(name=component, status="Affected"))
            err = ret.stderr.decode('utf-8').strip()
            if err:
                self.logger.error(utility._2sp(err))
        else:
            self.logger.info(template.format(name=component, status="OK"))

    def dist_git_merge_changes(self, images, rebase=False):
        """Method to merge changes from upstream into downstream

        Pulls both downstream and upstream repositories into a temporary dir.
        Merge is done by copying tracked files from upstream into downstream.

        Args:
            images (list): List of images to sync
            rebase (bool, optional): Specify if a rebase should be done instead
        """
        try:
            for image in images:
                name = image["name"]
                component = image["component"]
                branch = image["git_branch"]
                path = image["git_path"]
                url = image["git_url"]
                commands = image["commands"]
                pull_upstr = image.get("pull_upstream", True)
                repo = self._clone_downstream(component, branch)
                df_path = os.path.join(component, "Dockerfile")
                downstream_from = self.df_handler.get_from_df(df_path)
                self.logger.debug(f"Downstream_from: {downstream_from}\n")
                from_tag = self.conf.get("from_tag", "latest")
                if rebase or not pull_upstr:
                    self.df_handler.update_dockerfile(
                        df_path, from_tag, downstream_from=downstream_from
                    )
                    # It is possible for the git repository to have no changes
                    if repo.is_dirty():
                        commit = self.get_commit_msg(rebase, image)
                        if commit:
                            repo.git.commit("-am", commit)
                        else:
                            msg = "Not creating new commit in: "
                            self.logger.info(msg + component)
                else:
                    ups_name = name.split('-')[0]
                    # Clone upstream repository
                    ups_path = os.path.join('upstreams/', ups_name)
                    self.clone_upstream(url, ups_path, commands=commands)
                    # Save the upstream commit hash
                    ups_hash = Repo(ups_path).commit().hexsha
                    self.pull_upstream(component, path, url, repo, ups_name, commands)
                    self.df_handler.update_dockerfile(
                        df_path, from_tag, downstream_from=downstream_from
                    )
                    repo.git.add("Dockerfile")
                    # It is possible for the git repository to have no changes
                    if repo.is_dirty():
                        commit = self.get_commit_msg(rebase, image, ups_hash)
                        if commit:
                            repo.git.commit("-m", commit)
                        else:
                            msg = "Not creating new commit in: "
                            self.logger.info(msg + component)

                self._check_labels(df_path)
        finally:
            # Cleanup upstream repos
            shutil.rmtree("upstreams", ignore_errors=True)

    def _clone_downstream(self, component, branch):
        """Clones downstream dist-git repo"""
        # Do not set up downstream repo if it already exists
        if os.path.isdir(component):
            self.logger.info("Using existing downstream repo: " + component)
            repo = Repo(component)
        else:
            hostname_url = utility._get_hostname_url(self.conf)
            packager = utility._get_packager(self.conf)
            # if packager is fedpkg then namespace is `container` else `containers`
            namespace = "container" if packager == "fedpkg" else "containers"
            component_path = f"{namespace}/{component}"
            # If hostname_url is specified use `git` otherwise `packager` command.
            if hostname_url:
                cmd = "git"
                ccomponent = f"{hostname_url}/{component_path}.git"
            else:
                cmd = packager
                ccomponent = component_path

            self.logger.info("Cloning into: " + ccomponent)
            ret = subprocess.run([cmd, "clone", ccomponent],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            # If the clone failed, try once again with the containers prefix
            if ret.returncode != 0:
                template = "{} failed to clone {} with return value {}."
                raise RebuilderError(template.format(cmd, component,
                                                     ret.returncode))

            repo = Repo(component)
            repo.git.checkout(branch)
        return repo

    def push_changes(self, tmp, images):
        """Pushes changes for components into downstream dist-git repository"""
        # Check for kerberos ticket
        failed = []
        for image in images:
            component = image["component"]
            try:
                repo = Repo(component)
                # If a commit message is provided do a commit first
                if self.commit_msg and repo.is_dirty():
                    # commit_msg is set so it is always returned
                    commit = self.get_commit_msg(None, image)
                    repo.git.commit("-am", commit)
                if self.are_unpushed_commits_available(repo):
                    self.logger.info("Pushing: " + component)

                    repo.git.push()
                else:
                    self.logger.info(f"There are no unpushed commits."
                                     f" Push skipped for {component}.")
            except GitCommandError as e:
                failed.append(image)
                self.logger.error(e)

        if failed:
            self.logger.error("Failed pushing images:")
            for image in failed:
                self.logger.error(utility._2sp(image["component"]))
            self.logger.error("Please check the failures and push the changes manually.")

    # TODO: Multiple future branches?
    def merge_future_branches(self, images):
        """Merges current branch with future branches"""
        # Check for kerberos ticket
        failed = []
        for image in images:
            component = image["component"]
            branch = image["git_branch"]
            # TODO: config only has one future branch
            fb_list = [image["git_future"]]
            repo = self._clone_downstream(component, branch)
            for fb in fb_list:
                try:
                    repo.git.checkout(fb)
                    repo.git.merge(branch)
                    # print("Pushing into: {}".format(res))
                    self.logger.info("NOT Pushing into: {}".format(fb))
                    # repo.git.push()
                except GitCommandError as e:
                    failed.append(image)
                    self.logger.error(e)
                    continue
        if failed:
            self.logger.error("Failed merging images:")
            for image in failed:
                self.logger.error(utility._2sp(image["component"]))
            self.logger.error("Please check the failures and push the changes manually.")
