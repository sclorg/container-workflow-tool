import xmlrpc.client

import container_workflow_tool.utility as u


class KojiAPI:
    """Class for working with Koji."""

    def __init__(self, conf, logger, latest=False):
        url = "https://koji.fedoraproject.org/kojihub"
        self.brew = xmlrpc.client.ServerProxy(url, allow_none=True)
        self.nvrs = []
        self.buildinfo = {}
        self.conf = conf
        self.logger = logger if logger else u.setup_logger("koji")
        self.latest_by_nvr = latest

    def clear_cache(self):
        self.buildinfo = {}

    def get_time_built(self, nvr):
        """Gets time built from brew"""
        self.logger.debug("Getting time built for " + nvr)
        buildinfo = self.get_buildinfo(nvr)

        # NOTE: Let's try working with buildinfo['completion_time'] instead
        # task_id = self.buildinfo[nvr]['extra']['container_koji_task_id']
        # taskinfo = self.get_taskinfo(task_id)
        return buildinfo['completion_time']

    def get_taskinfo(self, task_id):
        """Gets task info from brew"""
        self.logger.debug("Getting taskinfo for task " + str(task_id))
        return self.brew.getTaskInfo(task_id)

    def get_listarchives(self, build_id):
        """Gets list archive for build_id"""
        self.logger.debug("Gettings list archives for build_id " + str(build_id))
        return self.brew.listArchives(build_id)

    def get_buildinfo(self, nvr):
        """Gets build info from brew"""
        if nvr not in self.buildinfo:
            self.logger.debug("Getting buildinfo for " + nvr)
            self.buildinfo[nvr] = self.brew.getBuild(nvr)
        else:
            self.logger.debug("Buildinfo for {} found in cache".format(nvr))
        return self.buildinfo[nvr]

    def get_all_builds(self, component, tag):
        return self.brew.listTagged(tag, None, None, None, None, component)

    def get_nvrs(self, images):
        """Gets nvrs from brew

        Returns:
            list of (str, str, str, obj): Brew nvrs.
                                          Format: (nvr, component, name, Bug)
        """
        if not self.nvrs:
            images_num = len(images)
            nvr_list = []
            self.logger.info("Fetching info from Brew... (0/{})".format(images_num))
            for i, image in enumerate(images, 1):
                if i % 10 == 0:
                    self.logger.info("Fetching info from Brew... ({}/{})".format(i, images_num))
                name = image["name"]
                component = image["component"]
                tag = image["build_tag"]
                nvr = self.get_nvr(tag, component)
                list_item = (nvr, name, component)
                nvr_list.append(list_item)
            self.logger.info("Fetching info from Brew... ({n}/{n})".format(n=images_num))
            self.nvrs = nvr_list

        return self.nvrs

    def get_nvr(self, tag, component):
        msg = "Getting latest nvr for component {} with tag {}"
        self.logger.debug(msg.format(component, tag))
        if self.latest_by_nvr:
            # Lets get all the builds and use the latest (release-wise)
            b = self.get_all_builds(component, tag)
            builds = sorted(b, key=lambda x: float(x['release']), reverse=True)
        else:
            # Get latest by time built
            builds = self.brew.getLatestBuilds(tag, None, component)

        nvr = builds[0]['nvr'] if builds else None
        if nvr is None:
            self.logger.warn("No build found for " + component + " using tag "
                             + tag)
        return nvr

    def get_build_hashid(self, build_id, arch="x86_64"):
        """ Get hash id of an image for a specific architecture from brew """
        msg = "Getting hash id for build {} on {} architecture"
        self.logger.debug(msg.format(str(build_id), arch))
        hashids = self.get_build_hashids(build_id)
        for hashid in hashids:
            if arch in hashid:
                ret = hashid
                break
        else:
            ret = None
        return ret

    def get_build_hashids(self, build_id):
        """ Get hash ids of an image for all its architectures from brew """
        hashids = []
        self.logger.debug("Getting hash ids for build " + str(build_id))
        for archive in self.brew.listArchives(build_id):
            hashid = archive['extra']['docker']['id']
            arch = archive['extra']['image']['arch']
            hashids.append((hashid, arch))
        return hashids
