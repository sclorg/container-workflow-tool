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
import shutil
import re

from container_workflow_tool.utility import setup_logger, _remove_file


class SyncHandler(object):
    """Class for handling with Dockerfile files."""

    def __init__(self, logger):
        self.logger = logger if logger else setup_logger("sync_handler")

    def copy_upstream2downstream(self, src_parent, dest_parent):
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
                self.logger.debug(f"rmtree {dest}")
                shutil.rmtree(dest)
            else:
                _remove_file(dest, self.logger)

            # Now copy the src to dest
            if os.path.islink(src) or not os.path.isdir(src):
                self.logger.debug(f"cp {src} {dest}")
                shutil.copy2(src, dest, follow_symlinks=False)
            else:
                self.logger.debug(f"cp -r {src} {dest}")
                shutil.copytree(src, dest, symlinks=True)

    def handle_dangling_symlinks(self, src_parent, dest_parent):
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
                    self.logger.debug(f"unlink {dest_file}")
                    os.unlink(dest_file)
                    src_full = os.path.join(os.path.dirname(src_path_content),
                                            os.readlink(src_path_content))
                    if os.path.isdir(src_full):
                        # In this case, when the source directory includes another symlinks outside
                        # of this directory, those wouldn't be fixed, so let's run the same function
                        # to fix dangling symlinks recursively.
                        self.logger.debug(f"cp -r {src_full} {dest_file}")
                        shutil.copytree(src_full, dest_file, symlinks=True)
                        self.handle_dangling_symlinks(src_parent, dest_parent)
                    else:
                        try:
                            self.logger.debug(f"cp {src_full} {dest_file}")
                            shutil.copy2(src_full, dest_file, follow_symlinks=False)
                        except FileNotFoundError:
                            self.logger.debug(f"Source file {src_full} does not exist")
