import os
import shutil
import re
import subprocess

from git import Repo
from git.exc import GitCommandError

import container_workflow_tool.utility as u
from container_workflow_tool.utility import RebuilderError


class DistgitAPI(object):
    """Class for working with dist-git."""

    def __init__(self, base_image, conf, rebuild_reason, logger):
        self.conf = conf
        self.base_image = base_image
        if not rebuild_reason:
            rebuild_reason = self.conf.rebuild_reason
        self.rebuild_reason = rebuild_reason.format(base_image=base_image)
        self.logger = logger if logger else u.setup_logger("dist-git")
        self.df_ext = self.conf.df_ext

        self.commit_msg = None

    def set_commit_msg(self, msg):
        """
        Set the commit message to some other than the default one.

        Args:
            msg(str): Message to be written into the commit.
        """
        self.commit_msg = msg

    def _get_from_df(self, dockerfile_path):
        res = None
        if os.path.exists(dockerfile_path):
            with open(dockerfile_path) as f:
                fdata = f.read()
            res = self._get_from(fdata)
        return res

    def _get_from(self, fdata: str) -> str:
        """Gets FROM field from a Dockerfile

        Args:
            fdata (str): String containing the Dockerfile

        Returns:
            str: FROM string
        """
        registry_base = None
        image_base = re.search('FROM (.*)\n', fdata)
        if image_base:
            registry_base = image_base.group(1)
        return registry_base

    def _set_from(self, fdata, from_tag):
        """
        Updates FROM field from a Dockerfile with value defined in configuration file

        Returns:
            str: Dockerfile content with updated tag field
        """
        self.logger.debug("Setting tag to: " + str(from_tag))
        base_image = self._get_from(fdata=fdata)
        self.logger.debug(f"Base image is: {base_image}")
        imagename_without_tag = base_image.split(':')[0]
        ret = re.sub("FROM (.*)\n",
                     f"FROM {imagename_without_tag}:{from_tag}\n", fdata)
        return ret

    def _update_variable_in_string(self, fdata: str = "", tag: str = "", tag_str: str = "", variable: str = ""):
        """
        Updates variable in string. Mainly used for updating test-openshift.yaml file.
        It replaces VERSION: VERSION_NUMBER -> VERSION: variable and
        It replaces OS: OS_VERSION -> OS: <os_name>"
        """
        self.logger.debug(f"Replaces variable of tag {tag} from {tag_str} to {variable}")
        ret = re.sub(rf"{tag}: {tag_str}", f"{tag}: \"{variable}\"", fdata)
        return ret

    def _update_test_openshift_yaml(self, test_openshift_yaml, version: str = "", short_name: str = ""):
        """
        Update test/test-openshift.yaml file with value VERSION_NUMBER and OS_NUMBER
        The file is used for CVP pipeline

        Args:
            test_openshift_yaml (Path): Path to test/test-openshift.yaml file
            version (str): version to be replaced with VERSION_NUMBER
            short_name (str): short_name to be replaced with CONTAINER_NAME
        """
        with open(test_openshift_yaml) as f:
            fdata = f.read()
        fdata = self._update_variable_in_string(fdata, "VERSION", "VERSION_NUMBER", version)
        os_name = "fedora"
        if self.conf.image_names == "RHEL8":
            os_name = "rhel8"
        if self.conf.image_names == "RHEL9":
            os_name = "rhel9"
        if self.conf.image_names == "RHSCL":
            os_name = "rhel7"
        fdata = self._update_variable_in_string(fdata, tag="OS", tag_str="OS_NUMBER", variable=os_name)
        fdata = self._update_variable_in_string(fdata, tag="SHORT_NAME", tag_str="CONTAINER_NAME", variable=short_name)
        with open(test_openshift_yaml, 'w') as f:
            f.write(fdata)

    def _update_dockerfile_rebuild(
            self, dockerfile_path, from_tag, downstream_from: str = "",
    ):
        with open(dockerfile_path) as f:
            fdata = f.read()
        res = self._set_from(fdata, from_tag)
        with open(dockerfile_path, 'w') as f:
            f.write(res)

    def update_dockerfile(self, df, from_tag, downstream_from: str = ""):
        """Updates basic fields of a Dockerfile. Sets from field

        Args:
            df (str): Path to the Dockerfile
            from_tag (str): value to be inserted into the from field
            downstream_from (str): value from downstream Dockerfile
        """
        self._update_dockerfile_rebuild(
            df, from_tag, downstream_from=downstream_from
        )

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
                self.logger.error(u._2sp(err))
        else:
            self.logger.info(template.format(name=component, status="OK"))

    def _do_git_reset(self, repo):
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

    def dist_git_changes(self, images, rebase=False):
        """Method to merge changes from upstream into downstream

        Pulls both downstream and upstream repositories into a temporary dir.
        Merge is done by copying tracked files from upstream into downstream.

        Args:
            rebase (bool, optional): Specify if a rebase should be done instead
        """
        try:
            for image in (images):
                name = image["name"]
                component = image["component"]
                branch = image["git_branch"]
                path = image["git_path"]
                url = image["git_url"]
                commands = image["commands"]
                pull_upstr = image.get("pull_upstream", True)
                repo = self._clone_downstream(component, branch)
                df_path = os.path.join(component, "Dockerfile")
                downstream_from = self._get_from_df(df_path)
                self.logger.debug(f"Downstream_from: {downstream_from}\n")
                from_tag = self.conf.get("from_tag", "latest")
                if rebase or not pull_upstr:
                    self.update_dockerfile(
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
                    self._clone_upstream(url, ups_path, commands=commands)
                    # Save the upstream commit hash
                    ups_hash = Repo(ups_path).commit().hexsha
                    self._pull_upstream(component, path, url, repo, ups_name, commands)
                    self.update_dockerfile(
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

    def _clone_upstream(self, url, ups_path, commands=None):
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

    def _copy_upstream2downstream(self, src_parent, dest_parent):
        """Copies content from upstream repo to downstream repo

        Copies all files/dirs/symlinks from upstream source to dist-git one by one,
        while removing previous if exists.

        Args:
            src_parent (string): path to source directory
            dest_parent (string): path to destination directory
        """
        for f in os.listdir(src_parent):
            dest = os.path.join(dest_parent, f)
            src = os.path.join(src_parent, f)
            # First remove the dest
            if os.path.isdir(dest):
                self.logger.debug("rmtree {}".format(dest))
                shutil.rmtree(dest)
            else:
                u._remove_file(dest, self.logger)

            # Now copy the src to dest
            if os.path.islink(src) or not os.path.isdir(src):
                self.logger.debug("cp {} {}".format(src, dest))
                shutil.copy2(src, dest, follow_symlinks=False)
            else:
                self.logger.debug("cp -r {} {}".format(src, dest))
                shutil.copytree(src, dest, symlinks=True)

    def _handle_dangling_symlinks(self, src_parent, dest_parent):
        """Replaces dangling symlinks in destination path with correct content

        We need to remove downstream's (destination) dangling symlinks here,
        because of files shared for more versions (s2i, root-common, test)
        in upstream (source).
        We do it by following first sources's symlink (not all symlinks) and
        copying rest of the target to the destination.

        Args:
            src_parent (string): path to source directory
            dest_parent (string): path to destination directory
        """
        for dest_root, dest_dirs, dest_files in os.walk(dest_parent):
            for dest_file_name in dest_files:
                dest_file = os.path.join(dest_root, dest_file_name)
                # Look for danging symlinks to relative path, then copy the content
                # from source, following the first symlink
                if os.path.islink(dest_file) and not os.path.isabs(os.readlink(dest_file)):
                    dest_target = os.path.join(os.path.dirname(dest_file), os.readlink(dest_file))
                    msg = f"looking for dangling symlink {dest_file} (that points to {dest_target})"
                    self.logger.debug(msg)
                    if os.path.exists(dest_target):
                        continue
                    # We found a dangling symlink to relative path,
                    # so we need to use the matching path in source,
                    # which means removing destination name
                    # from destination and adding it to source root
                    dest_path_rel = re.sub(
                        r"^{comp}{sep}".format(comp=dest_parent, sep=os.path.sep),
                        "",
                        dest_file
                    )
                    src_path_content = os.path.join(src_parent, dest_path_rel)
                    self.logger.debug("unlink {dest}".format(dest=dest_file))
                    os.unlink(dest_file)
                    src_full = os.path.join(os.path.dirname(src_path_content),
                                            os.readlink(src_path_content))
                    if os.path.isdir(src_full):
                        # In this case, when the source directory includes another symlinks outside
                        # of this directory, those wouldn't be fixed, so let's run the same function
                        # to fix dangling symlinks recursively.
                        self.logger.debug("cp -r {src} {dest}".format(src=src_full, dest=dest_file))
                        shutil.copytree(src_full, dest_file, symlinks=True)
                        self._handle_dangling_symlinks(src_parent, dest_parent)
                    else:
                        self.logger.debug("cp {src} {dest}".format(src=src_full, dest=dest_file))
                        shutil.copy2(src_full, dest_file, follow_symlinks=False)

    def _pull_upstream(self, component, path, url, repo, ups_name, commands):
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
        self._copy_upstream2downstream(cp_path, component)
        self._handle_dangling_symlinks(cp_path, component)
        # If README.md exists but help.md does not, create a symlink
        help_md = os.path.join(component, "help.md")
        readme_md = os.path.join(component, "README.md")
        if not os.path.isfile(help_md):
            if os.path.isfile(readme_md):
                os.symlink('README.md', help_md)
                repo.git.add('help.md')
            else:
                # Report warning if help.md does not exists
                self.logger.warn("help.md file missing")
        # Add all the changes and remove those we do not want
        test_openshift_yaml_file = os.path.join(component, "test", "test-openshift.yaml")
        if os.path.exists(test_openshift_yaml_file):
            self._update_test_openshift_yaml(test_openshift_yaml_file, path, short_name=ups_name)

        repo.git.add("*")
        self._do_git_reset(repo)
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
        repo = Repo(component)
        version = os.path.basename(cp_path)
        link_name = os.path.join(component, version)
        if not os.path.islink(link_name):
            try:
                os.symlink(".", link_name)
                repo.git.add(version)
            except FileExistsError:  # noqa: F821 - Doesnt see built-ins?
                t = "Failed creating symlink '{}' -> '.', file already exists."
                raise u.RebuilderError(t.format(link_name))

        # Run post upstream pull hook
        self._post_upstream_pull(cp_path, component)

    def _post_upstream_pull(sefl, upstream_path, downstream_path):
        """Post upstream pull hook"""
        pass

    def _clone_downstream(self, component, branch):
        """Clones downstream dist-git repo"""
        # Do not set up downstream repo if it already exists
        if os.path.isdir(component):
            self.logger.info("Using existing downstream repo: " + component)
            repo = Repo(component)
        else:
            hostname_url = u._get_hostname_url(self.conf)
            packager = u._get_packager(self.conf)
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

    def _get_unpushed_commits(self, repo):
        """
        Get unpushed commits
        :param repo: repo name to check for unpushed commits
        :return: List of commits or empty array
        """
        branch = repo.active_branch.name
        # Get a list of commits that have not been pushed to remote
        select = "origin/" + branch + ".." + branch
        commits = [i for i in repo.iter_commits(select)]
        return commits

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
                if self._get_unpushed_commits(repo):
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
                self.logger.error(u._2sp(image["component"]))
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
                self.logger.error(u._2sp(image["component"]))
            self.logger.error("Please check the failures and push the changes manually.")

    def show_git_changes(self, tmp, components=None, diff=False):
        """Shows changes made to tracked files in local downstream repositories

        Walks through all repositories and calls 'git-show' or 'git-diff' on each of them.

        Args:
            tmp (str): Path to the directory that is used to store git repositories
            components (list of str, optional): List of components to show changes for
            diff (boolean, optional): Controls whether the method calls git-show or git-diff
        """
        # Function to check if a path contains a git repository
        def is_git(x): return os.path.isdir(os.path.join(x, '.git'))
        files = None
        command = 'diff' if diff else 'show'
        # Create a list of repository paths
        if not components:
            # Get the whole subdirectory
            files = [f.path for f in os.scandir(tmp) if is_git(f.path)]
        elif isinstance(components, list):
            files = [path for path in [os.path.join(tmp, c) for c in components] if is_git(path)]
        elif isinstance(components, str) and is_git(os.path.join(tmp, components)):
            files = [os.path.join(tmp, components)]
        else:
            raise u.RebuilderError("Unknown component: {}".format(str(components)))
        if not files:
            self.logger.warn("No git repositories found in directory " + tmp)
        # Walk through the repositories and show changes made in the last commit
        for path in files:
            repo = Repo(path)
            # Only show changes if there are unpushed commits to show
            # or we only want the diff of unstaged changes
            if self._get_unpushed_commits(repo) or diff:
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
