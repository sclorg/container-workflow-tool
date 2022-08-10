# description     : Script for helping with the rebuild of container images.
# author          : pkubat@redhat.com
# notes           : Rewritten from a shell script originally created by hhorak@redhat.com.
# python_version  : 3.x

import subprocess
import os
import shutil
import re
import tempfile
import pprint
import getpass
import logging

from git import Repo, GitError
from typing import List, Any
from pathlib import Path

import container_workflow_tool.utility as u
from container_workflow_tool.koji import KojiAPI
from container_workflow_tool.distgit import DistgitAPI
from container_workflow_tool.utility import RebuilderError
from container_workflow_tool.config import Config


class ImageRebuilder:
    """Class for rebuilding Container images."""

    def __init__(self,
                 base_image: str,
                 rebuild_reason: str = None,
                 config: str = "default.yaml",
                 release: str = "current"):
        """ Init method of ImageRebuilder class

        Args:
            base_image (str): image id to be used as a base image
            config (str, optional): configuration file to be used
            rebuild_reason (str, optional): reason for the rebuild,
                                            used in commit
        """
        self.base_image = base_image

        self._brewapi: KojiAPI = None
        self._distgit: DistgitAPI = None
        self.commit_msg = None
        self.args = None
        self.tmp_workdir: str = None
        self.repo_url = None
        self.jira_header = None

        self.conf_name = config
        self.rebuild_reason = rebuild_reason
        self.do_image = None
        self.exclude_image = None
        self.do_set = None
        self.check_script = None
        self.image_set = None
        self.disable_klist = None
        self.output_file = None
        self.latest_release = None

        self.logger = self._setup_logger()
        self.set_config(self.conf_name, release=release)

    @classmethod
    def from_args(cls, args) -> Any:
        """
        Creates an ImageRebuilder instance from argparse arguments.
        """
        config = args.config if args.config else 'default.yaml'
        config_path, image_set = u._split_config_path(config)
        rebuilder = ImageRebuilder(base_image=args.base, config=config_path, release=image_set)
        rebuilder._setup_args(args)
        rebuilder.setup_log_to_file()
        return rebuilder

    def setup_log_to_file(self):
        # File handler
        if self.output_file:
            out_file = Path(self.output_file)
            # If file is not absolute lets create out_file from current directory
            if not out_file.is_absolute():
                out_file = Path.cwd() / self.output_file
            file_handler = logging.FileHandler(out_file)
            file_handler.setLevel(logging.INFO)
            file_format_str = "%(message)s"
            file_formatter = logging.Formatter(file_format_str)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

    def _setup_args(self, args):
        self.args = args

        if args.config:
            config_path, image_set = u._split_config_path(args.config)
            self.set_config(config_path, image_set)
        if args.tmp:
            self.set_tmp_workdir(args.tmp)
        if args.clear_cache:
            self.clear_cache()
        if args.do_image:
            self.set_do_images(args.do_image)
        if args.exclude_image:
            self.set_exclude_images(args.exclude_image)
        if args.do_set:
            self.set_do_set(args.do_set)
        self.logger.setLevel(u._transform_verbosity(args.verbosity))

        # Command specific
        # TODO: generalize?
        if getattr(args, 'repo_url', None) is not None and args.repo_url:
            self.set_repo_url(args.repo_url)
        if getattr(args, 'commit_msg', None) is not None:
            self.set_commit_msg(args.commit_msg)
        if getattr(args, 'rebuild_reason', None) is not None and args.rebuild_reason:
            self.rebuild_reason = args.rebuild_reason
        if getattr(args, 'check_script', None) is not None and args.check_script:
            self.check_script = args.check_script
        if getattr(args, 'disable_klist', None) is not None and args.disable_klist:
            self.disable_klist = args.disable_klist
        if getattr(args, 'latest_release', None) is not None and args.latest_release:
            self.latest_release = args.latest_release
        if getattr(args, 'output_file', None) is not None and args.output_file:
            self.output_file = args.output_file

        # Image set to build
        if getattr(args, 'image_set', None) is not None and args.image_set:
            self.image_set = args.image_set

    def _get_set_from_config(self, layer: str) -> str:
        i = getattr(self.conf, layer, [])
        if i is None:
            err_msg = "Image set '{}' not found in config.".format(layer)
            raise RebuilderError(err_msg)
        return i

    @property
    def distgit(self):
        if not self._distgit:
            self._distgit = DistgitAPI(self.base_image, self.conf,
                                      self.rebuild_reason,
                                      self.logger.getChild("dist-git"))
        return self._distgit

    @property
    def brewapi(self):
        if not self._brewapi:
            self._brewapi = KojiAPI(self.conf, self.logger.getChild("koji"),
                                   self.latest_release)
        return self._brewapi

    def _setup_logger(self, level=logging.INFO, user_logger=None, name=__name__):
        # If a logger is already set up, do not setup a new one
        if hasattr(self, "logger") and self.logger:
            return self.logger
        # If a logger has been provided, do not setup own
        if user_logger and isinstance(user_logger, logging.Logger):
            logger = user_logger
        else:
            logger = u.setup_logger(name, level)

        self.logger = logger
        return logger

    def _check_kerb_ticket(self):
        if not self.disable_klist:
            ret = subprocess.run(["klist"], stdout=subprocess.DEVNULL)
            if ret.returncode:
                raise(RebuilderError("Kerberos token not found."))

    def _change_workdir(self, path: str):
        self.logger.info("Using working directory: " + path)
        os.chdir(path)

    def _get_tmp_workdir(self, setup_dir: bool = True) -> str:
        self._check_base(self.base_image)
        # Check if the workdir has been set by the user
        if self.tmp_workdir:
            return self.tmp_workdir
        tmp = None
        tmp_id = self.base_image.replace(":", "-")
        # Check if there is an existing tempdir for the build
        for f in os.scandir(tempfile.gettempdir()):
            if os.path.isdir(f.path) and f.name.startswith(tmp_id):
                tmp = f.path
                break
        else:
            if setup_dir:
                tmp = tempfile.mkdtemp(prefix=tmp_id)
        return tmp

    def set_do_images(self, val):
        self.do_image = val

    def set_exclude_images(self, val):
        self.exclude_image = val

    def set_do_set(self, val):
        self.do_set = val

    def _check_base(self, base_image):
        if not base_image:
            raise RebuilderError("Base image needs to be set.")

    def _get_images(self) -> List:
        images: List = []
        if self.do_set:
            # Use only the image sets the user asked for
            for layer in self.do_set:
                images += self._get_set_from_config(layer)
        else:
            # Go through all known layers and create a single image list
            for (order, layer) in self.conf.layers.items():
                i = getattr(self.conf, layer, [])
                images += i
        return self._filter_images(images)

    def _filter_images(self, base: List) -> List:
        if self.do_image:
            return [i for i in base if i["component"] in self.do_image]
        elif self.exclude_image:
            return [i for i in base if i["component"] not in self.exclude_image]
        else:
            return base

    def _prebuild_check(self, image_set: List, branches: List = None):
        tmp = self._get_tmp_workdir(setup_dir=False)
        if not tmp:
            msg = "Temporary directory structure does not exist. Pull upstream first."
            raise RebuilderError(msg)
        self.logger.info("Checking for correct repository configuration ...")
        releases = branches
        for image in image_set:
            component = image["component"]
            cwd = os.path.join(tmp, component)
            try:
                repo = Repo(cwd)
            except GitError as e:
                self.logger.error("Failed to open repository for {}", component)
                raise e
            # This checks if any of the releases can be found in the name of the checked-out branch
            if releases and not [i for i in releases if i in str(repo.active_branch)]:
                msg = f"Unexpected active branch for {component}: {repo.active_branch}"
                raise RebuilderError(msg)

    def _build_images(self, image_set, custom_args: List = None, branches: List = None):
        if not image_set:
            # Nothing to build
            self.logger.warn("No images to build, exiting.")
            return
        if not branches:
            # Fill defaults from config if not provided
            for release in self.conf.releases:
                branches += [self.conf.releases[release]["current"]]
        self._prebuild_check(image_set, branches)

        procs = []
        triggers = []
        tmp = self._get_tmp_workdir(setup_dir=False)
        for image in image_set:
            component = image["component"]
            cwd = os.path.join(tmp, component)
            self.logger.info(f"Building image {component} ...")
            args = [u._get_packager(self.conf), "container-build"]
            if custom_args:
                args.extend(custom_args)
            proc = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    universal_newlines=True)
            # Append the process and component information for later use
            procs.append((proc, image))

        self.logger.info("Fetching tasks...")
        for proc, image in procs:
            component = image["component"]
            self.logger.debug(f"Query component: {component}")
            # Iterate until a taskID is found
            for stdout in iter(proc.stdout.readline, ""):
                if "taskID" in stdout:
                    self.logger.info(f"{component} - {stdout.strip()}")
                    break
            else:
                # If we get here the command must have failed
                # The error will get printed out later when getting all builds
                self.logger.warning(f"Could not find task for {component}!")

        self.logger.info("Waiting for builds...")
        timeout = 30
        while procs:
            self.logger.debug("Looping over all running builds")
            for proc, image in procs:
                out = err = None
                component = image["component"]
                try:
                    self.logger.debug(f"Waiting {timeout} seconds for {component}")
                    out, err = proc.communicate(timeout=timeout)
                except subprocess.TimeoutExpired:
                    msg = "{} not yet finished, checking next build"
                    self.logger.debug(msg.format(component))
                    self.logger.debug(f"{component} not yet finished, checking next build")
                    continue
                if proc.returncode != 0:
                    self.logger.error(f"{component} build has failed")
                else:
                    self.logger.info(f"{component} build has finished")
                    # If this image triggers a new layer, build it
                    if "trigger" in image:
                        triggers.append((component, image["trigger"]))

                self.logger.info(f"{component} build has finished")
                if err:
                    # Write out stderr if we encounter an error
                    err = u._4sp(err)
                    self.logger.error(err)

                procs.remove((proc, image))

        for component, trigger in triggers:
            msg = "Triggering layered builds on image %s..."
            self.logger.info(msg, component)
            self.build_images(trigger)

    def _get_config_path(self, config: str) -> str:
        if not os.path.isabs(config):
            base_path = os.path.abspath(__file__)
            dir_path = os.path.dirname(base_path)
            path = os.path.join(dir_path, "config/", config)
        else:
            path = config
        return path

    def _not_yet_implemented(self):
        print("Method not yet implemented.")

    def get_brew_builds(self, print_time: bool = True) -> List[str]:
        """Returns information about builds in brew

        Args:
            print_time (bool, optional): Print time finished for a build.

        Returns:
            str: Resulting brew build text
        """
        output = []
        header = "||Component||Build||Image_name||"
        if print_time:
            header += "Build finished||"
        header += "Archives||"
        output.append(header)
        nvrs = (self.brewapi.get_nvrs(self._get_images()))
        for item in nvrs:
            nvr, name, component, *rest = item
            # No nvr found for the image, might not have been built
            if nvr is None:
                continue
            else:
                template = "|{0}|{1}|{2}|"
            vr = re.search(".*-([^-]*-[^-]*)$", nvr).group(1)
            build_id = self.brewapi.get_buildinfo(nvr)["build_id"]
            archives = self.brewapi.get_listarchives(build_id)
            archive = archives[0]["extra"]
            name = archive["docker"]["config"]["config"]["Labels"]["name"]
            image_name = f"{name}:{vr}"
            result = template.format(component, nvr, image_name)
            if print_time:
                result += self.brewapi.get_time_built(nvr) + '|'
            result += str(len(archives))
            output.append(result)
        return output

    def set_config(self, conf_name: str, release: str = "current"):
        """
        Use a configuration file other than the current one.
        The configuration file used must be located in the standard 'config' directory.

        Args:
            config(str): Name of the configuration file (filename)
            release(str, optional): ID of the release to be used inside the config
        """
        path = self._get_config_path(conf_name)
        self.logger.debug("Setting config to {}", path)
        with open(path) as f:
            newconf = Config(f, release)
        self.conf = newconf
        # Set config for every module that is set up
        if self.brewapi:
            self.brewapi.conf = newconf
        if self.distgit:
            self.distgit.conf = newconf

    def set_tmp_workdir(self, tmp: str):
        """
        Sets the temporary working directory to the one provided.
        The directory has to already exist.

        Args:
            tmp(str): location of the directory to be used
        """
        if os.path.isdir(tmp):
            self.tmp_workdir = os.path.abspath(tmp)
        else:
            raise RebuilderError("Provided working directory does not exist.")

    def set_commit_msg(self, msg: str):
        """
        Set the commit message to some other than the default one.

        Args:
            msg(str): Message to be written into the commit.
        """
        self.distgit.set_commit_msg(msg)

    def clear_cache(self):
        """Clears various caches used in the rebuilding process"""

        self.logger.info("Removing cached data and git storage.")
        # Clear ondisk storage for git and the brew cache
        tmp = self._get_tmp_workdir(setup_dir=False)
        shutil.rmtree(tmp, ignore_errors=True)
        # If the working directory has been set by the user, recreate it
        if self.tmp_workdir:
            os.makedirs(tmp)

        # Clear koji object caches
        self.nvrs = []
        if self.brewapi:
            self.brewapi.clear_cache()

    def set_repo_url(self, repo_url):
        """Repofile url setter

        Sets the url of .repo file used for the build.

        Args:
            repo_url: url of .repo file used for the build
        """
        self.repo_url = repo_url

    def list_images(self):
        """Prints list of images that we work with"""
        for i in self._get_images():
            self.logger.info(i["component"])

    def print_upstream(self):
        """Prints the upstream name and url for images used in config"""
        for i in self._get_images():
            ups_name = re.search(r".*\/([a-zA-Z0-9-]+).git",
                                 i["git_url"]).group(1)
            msg = f"{i.get('component')} {i.get('name')} {ups_name} " \
                  f"{i.get('git_url')} {i.get('git_path')} {i.get('git_branch')}"
            self.logger.info(msg)

    def show_config_contents(self):
        """Prints the symbols and values of configuration used"""
        for key in self.conf:
            value = getattr(self.conf, key)
            # Do not print clutter the output with unnecessary content
            if key in ["raw"]:
                continue
            print(key + ":")
            pprint.pprint(value, compact=True, width=256, indent=4)

    def build_images(self, image_set=None):
        """
        Build images specified by image_set (or self.image_set)
        """
        if image_set is None and self.image_set is None:
            raise RebuilderError("image_set is None, build cancelled.")
        if image_set is None:
            image_set = self.image_set
        image_config = self._get_set_from_config(image_set)
        images = self._filter_images(image_config)
        self._build_images(images)

    def print_brew_builds(self, print_time: bool = True):
        """Prints information about builds in brew

        Args:
            print_time (bool, optional): Print time finished for a build.

        Returns:
            str: Resulting brew build text
        """
        for builds in self.get_brew_builds(print_time=print_time):
            self.logger.info(builds)

    def pull_downstream(self):
        """
        Pulls downstream dist-git repositories and does not make any further changes to them

        Additionally runs a script against each repository if check_script is set,
        checking its exit value.
        """
        self._check_kerb_ticket()
        tmp = self._get_tmp_workdir()
        self._change_workdir(tmp)
        images = self._get_images()
        for i in images:
            self.distgit._clone_downstream(i["component"], i["git_branch"])
        # If check script is set, run the script provided for each config entry
        if self.check_script:
            for i in images:
                self.distgit.check_script(i["component"], self.check_script,
                                          i["git_branch"])

    def pull_upstream(self):
        """
        Pulls upstream git repositories and does not make any further changes to them

        Additionally runs a script against each repository if check_script is set,
        checking its exit value.
        """
        tmp = self._get_tmp_workdir()
        self._change_workdir(tmp)
        images = self._get_images()
        for i in images:
            # Use unversioned name as a path for the repository
            ups_name = i["name"].split('-')[0]
            self.distgit._clone_upstream(i["git_url"],
                                         ups_name,
                                         commands=i["commands"])
        # If check script is set, run the script provided for each config entry
        if self.check_script:
            for i in images:
                ups_name = i["name"].split('-')[0]
                self.distgit.check_script(i["component"], self.check_script,
                                          os.path.join(ups_name, i["git_path"]))

    def push_changes(self):
        """Pushes changes for all components into downstream dist-git repository"""
        # Check for kerberos ticket
        self._check_kerb_ticket()
        tmp = self._get_tmp_workdir(setup_dir=False)
        if not tmp:
            msg = "Temporary directory structure does not exist. Pull upstream/rebase first."
            raise RebuilderError(msg)
        self._change_workdir(tmp)
        images = self._get_images()

        self.distgit.push_changes(tmp, images)

    def dist_git_rebase(self):
        """
        Do a rebase against a new base/s2i image.
        Does not pull in upstream changes of layered images.
        """
        self.dist_git_changes(rebase=True)

    def dist_git_changes(self, rebase: bool = False):
        """Method to merge changes from upstream into downstream

        Pulls both downstream and upstream repositories into a temporary directory.
        Merge is done by copying tracked files from upstream into downstream.

        Args:
            rebase (bool, optional): Specifies whether a rebase should be done instead.
        """
        # Check for kerberos ticket
        self._check_kerb_ticket()
        tmp = self._get_tmp_workdir()
        self._change_workdir(tmp)
        images = self._get_images()
        self.distgit.dist_git_changes(images, rebase)
        self.logger.info("\nGit location: " + tmp)
        if self.args:
            tmp_str = ' --tmp ' + self.tmp_workdir if self.tmp_workdir else '"'
            self.logger.info("You can view changes made by running:")
            self.logger.info(f"cwt --base {self.base_image} {tmp_str} git show")
        if self.args:
            self.logger.info(
                "To push and build run:"
                "cwt git push && cwt build"
                "[base/core/s2i] --repo-url link-to-repo-file")

    def merge_future_branches(self):
        """Merges current branch with future branches"""
        # Check for kerberos ticket
        self._check_kerb_ticket()
        tmp = self._get_tmp_workdir()
        self._change_workdir(tmp)
        images = self._get_images()
        self.distgit.merge_future_branches(images)

    def show_git_changes(self, components: List = None):
        """Shows changes made to tracked files in local downstream repositories

        Args:
            components (list of str, optional): List of components to show changes for
        Walks through all downstream repositories and calls 'git-show' on each of them.
        """
        if not components:
            images = self._get_images()
            components = [i["component"] for i in images]
        tmp = self._get_tmp_workdir()
        self._change_workdir(tmp)
        self.distgit.show_git_changes(tmp, components)
