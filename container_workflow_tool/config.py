import yaml


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
        config = yaml.load(yaml_file)
        for key in config[release]:
            self[key] = config[release][key]

        urls = config["urls"]
        images = config["images"]
        self["layers"] = config["layer_ordering"]
        self["packager_util"] = config["packager_utils"]
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
                image["commands"] = image.get("commands", commands)
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
                result.append(image)

            self[layer_id] = result
