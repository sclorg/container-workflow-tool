import sys
import argparse
import os
import logging

import textwrap


class RebuilderError(Exception):
    pass


class ArgParser(argparse.ArgumentParser):
    def print_help(self, file=None):
        if file is None:
            file = sys.stdout
        self._print_message(self.format_usage(), file)


# Utility textwrap functions
def _2sp(a): return textwrap.indent(a, '  ')


def _4sp(a): return textwrap.indent(a, '    ')


# Utility functions
def flatten_list(input_list):
    flattened = []
    for sl in input_list:
        if not isinstance(sl, list):
            flattened.append(sl)
        else:
            for ll in sl:
                flattened.append(ll)
    return flattened


def _transform_verbosity(value):
    return ((value - 6) * -10)


def _remove_file(path, logger=None):
    if os.path.islink(path):
        if logger:
            logger.debug("unlink {}".format(path))
        os.unlink(path)
    elif os.path.exists(path):
        if logger:
            logger.debug("rm {}".format(path))
        os.remove(path)


def _get_packager(config):
    # Try to read which packager to use from the config file, default to rhpkg
    packager = getattr(config, 'packager_util', "fedpkg")
    return packager


def _get_hostname_url(config):
    # Try to read which packager to use from the config file
    # default to "https://src.fedoraproject.org"
    git_url = getattr(config, "hostname_url", None)
    return git_url


def setup_logger(logger_id, level=logging.INFO):
    logger = logging.getLogger(logger_id)
    logger.setLevel(level)
    format_str = "%(name)s - %(levelname)s: %(message)s"
    # Debug handler
    debug = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(format_str)
    debug.setLevel(logging.DEBUG)
    debug.addFilter(lambda r: True if r.levelno == logging.DEBUG else False)
    debug.setFormatter(formatter)
    logger.addHandler(debug)
    # Info handler
    info = logging.StreamHandler(sys.stdout)
    info.setLevel(logging.DEBUG)
    info.addFilter(lambda r: True if r.levelno == logging.INFO else False)
    logger.addHandler(info)
    # Warning, error, critical handler
    stderr = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(format_str)
    stderr.setLevel(logging.WARN)
    stderr.addFilter(lambda r: True if r.levelno >= logging.WARN else False)
    stderr.setFormatter(formatter)
    logger.addHandler(stderr)
    return logger
