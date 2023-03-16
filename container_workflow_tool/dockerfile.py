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
import re

from container_workflow_tool.utility import setup_logger, RebuilderError


class DockerfileHandler:
    """Class for handling with Dockerfile files."""

    def __init__(self, base_image, logger=None):
        self.base_image = base_image
        self.logger = logger if logger else setup_logger("dockerfile")

    def get_from_df(self, dockerfile_path):
        with open(dockerfile_path) as f:
            fdata = f.read()
        return self.get_from(fdata)

    def get_from(self, fdata: str):
        """Gets FROM field from a Dockerfile

        Args:
            fdata (str): String containing the Dockerfile

        Returns:
            str: FROM string
        """
        image_base = re.search('FROM (.*)\n', fdata)
        if image_base and image_base.group(1) != "":
            return image_base.group(1)
        raise RebuilderError("FROM field is missing")

    def set_from(self, fdata, from_tag):
        """
        Updates FROM field from a Dockerfile with value defined in configuration file

        Returns:
            str: Dockerfile content with updated tag field
        """
        self.logger.debug(f"Setting tag to: {from_tag}")
        try:
            base_image = self.get_from(fdata=fdata)
        except RebuilderError:
            return fdata
        self.logger.debug(f"Base image is: {base_image}")
        imagename_without_tag = base_image.split(':')[0]
        ret = re.sub("FROM (.*)\n",
                     f"FROM {imagename_without_tag}:{from_tag}\n", fdata)
        return ret

    def update_dockerfile(self, df: str, from_tag: str, downstream_from: str = ""):
        """Updates basic fields of a Dockerfile. Sets from field

        Args:
            df (str): Path to the Dockerfile
            from_tag (str): value to be inserted into the from field
            downstream_from (str): value from downstream Dockerfile
        """
        if os.path.exists(df):
            with open(df) as f:
                fdata = f.read()
            res = self.set_from(fdata, from_tag)
            with open(df, 'w') as f:
                f.write(res)
