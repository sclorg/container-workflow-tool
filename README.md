Container Workflow Tool
=======================
[![Docker Repository on Quay](https://quay.io/repository/rhscl/cwt-generator/status "Docker Repository on Quay")](https://quay.io/repository/rhscl/cwt-generator)


A python3 tool to make rebuilding container images easier by automating several steps of the process.

Motivation
----------

The actual rebuild of container images consists of several steps that have been so far done manually. Some of these steps are:

 * **Rebase against upstream repository**
 * **Check the changes made by the rebase**
 * **Push the changes into dist-git and run the build**

All of the steps are currently automated or semi-automated by `cwt` (but still need to be manually started). This should help a bit with the image rebuild workflow.

Requirements
------------

* python3
* python3-GitPython
* python3-requests-kerberos
* fedpkg

Options
-------

```
usage: cwt [options] command
    Command:
        koji            - List builds, base images, hash ids
        build           - Command for building images
        git             - Work with upstream/downstream git repositories
        utils           - Other actions tied to the rebuild (communication, repository preparation etc.)

    Options:
        -v, --verbosity      - Verbosity level, 1 (Critical only) - 5 (Debug messages), default 4 (Info)
        --base               - Specific base image release, required for some actions
        --clear-cache        - Clears tmp dir before running the command
        --latest-release     - Work with latest brew builds by release value
        --config             - Overrides default configuration file, expects the name of file a inside the config folder, optionally takes image_set argument
                               example usage: --config default.yaml:fedora27
        --do-image           - Use a custom set of images instead of all from the config (use dist-git names)
        --exclude-image      - Exclude an image from the list of images defined by config (use dist-git names)
        --do-set             - Use a specific set of images instead of all from the config (use dist-git names)
        --tmp                - Overrides default temporary working directory
        --disable-klist      - Disables getting kerberos token by klist
```

To get the usage of a specific command, you can run:

    cwt command --help

container-workflow-tool in the quay.io registry
-----------------------------------------------
`container-workflow-tool` is automatically built and pushed in
[quay.io/rhscl/cwt-generator](https://quay.io/repository/rhscl/cwt-generator) as soon as changes
are merged into `master` branch.

Test
----
This repository also contains test suites for python's `unittest` framework that check the basic functionality of cwt.
These test can be run directly from the repository's root via Makefile:

    make test

If you do not need to run all of the test cases provided you can run a module-specific subset like this:

    make test_distgit

If you want to run all the test cases in container, run it like this:

```bash
make test-in-container
```
