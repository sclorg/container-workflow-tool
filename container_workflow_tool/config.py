# Loader class and construct_include function based on
# code by Josh Bode, shared under the MIT license:
# https://gist.github.com/joshbode/569627ced3076931b02f

import os

import yaml
from typing import IO


class Loader(yaml.SafeLoader):
    """YAML Loader with `!include` constructor."""

    def __init__(self, stream):
        """Initialise Loader."""

        try:
            self._root = os.path.split(stream.name)[0]
        except AttributeError:
            self._root = os.path.curdir

        super().__init__(stream)


def construct_include(loader, node):
    """Include file referenced at node."""

    arg = os.path.abspath(os.path.join(loader._root,
                                       loader.construct_scalar(node)))
    # filename[:key]
    arg_list = arg.split(':')
    filename = arg_list[0]
    with open(filename, 'r') as f:
        yaml_config = yaml.load(f, Loader)
    if len(arg_list) == 2:
        # Key argument present, return only the key value from included file
        yaml_config = yaml_config[arg_list[1]]
    return yaml_config


class Config(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError

    def __setattr__(self, key, value):
        self[key] = value

    # TODO: Maybe use the config as base and remove unneeded releases?
    def __init__(self, yaml_file, release="current"):
        # First add the include constructor to be able to share config values
        yaml.add_constructor('!include', construct_include, Loader)
        yaml_config = yaml.load(yaml_file, Loader)
        if "v1" in yaml_config:
            # v1 config
            config = yaml_config["v1"]
            for key in config["cwt"]:
                config[key] = config["cwt"][key]
        else:
            # v0 config, no changes needed
            config = yaml_config
        for key in config[release]:
            self[key] = config[release][key]

        urls = config["urls"]
        images = config["images"]
        self["layers"] = config["layer_ordering"]
        self["packager_util"] = config["packager_utils"]
        self["hostname_url"] = config.get("hostname_url", "")
        self["product"] = config.get("product", "")
        self["image_names"] = config.get("image_names", "")
        self["rebuild_reason"] = config.get("rebuild_reason", "")
        self["ignore_files"] = config["ignore_files"]
        self["groups"] = config.get("groups", {})
        self["mails"] = config.get("mails", {})
        self["df_ext"] = config.get("df_ext", ".fedora")
        self["raw"] = config
        commands = config.get("commands", {})
        # Parse the image layers
        for (layer_id, image_list) in self["image_sets"].items():
            result = []
            if not image_list:
                # Empty image list (possbly redefined), just append empty list
                self[layer_id] = result
                continue

            for i in image_list:
                t = "build_tag"
                image = images[i]
                image["name"] = i
                image["git_url"] = urls[image["git_url"]]
                b = image["git_branch"]
                # Use the release branch if no future branches provided
                fb = image["git_future"] if "git_future" in image else b
                # Use global commands, if does not exist per image
                image_commands = image.get("commands", {})
                image["commands"] = commands.copy()
                image["commands"].update(image_commands)
                # Use global build tag if no image specific is provided
                tag = image[t] if t in image else self[t]
                if "releases" in self:
                    for r in self["releases"].values():
                        # Replace release IDs in branches
                        if r["id"] in b:
                            b = b.replace(r["id"], r["current"])
                        if r["id"] in fb:
                            # TODO: What if there are multiple future releases?
                            fb = fb.replace(r["id"], r["future"][0])
                        # Create build tag from release
                        if r["id"] in tag:
                            image[t] = tag.replace(r["id"], r["current"])

                image["git_branch"] = b
                image["git_future"] = fb
                if "namespace" not in image:
                    image["namespace"] = self.get("namespace", "")
                result.append(image)

            self[layer_id] = result
