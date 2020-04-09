import unittest
import os
import sys
from io import StringIO
import logging

from container_workflow_tool.main import ImageRebuilder


def create_logger(out_file, level, c_name=None):
    # Unique name for a given combination, allow overriding
    name = c_name if c_name else "test-"+str(level)+str(out_file.name)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.hasHandlers():
        format_str = "%(levelname)s: %(message)s"
        handler = logging.StreamHandler(out_file)
        formatter = logging.Formatter(format_str)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


class TestCaseBase(unittest.TestCase):
    def setUp(self, c_logger=None):
        self.cwd = os.getcwd()
        self.component = 's2i-base'
        self.ir = ImageRebuilder('Testing')

        self.ir.set_config('default.yaml', release="rawhide")
        # Partner BZ testing
        self.ir.rebuild_reason = "Unit testing"
        self.ir.disable_klist = True
        self.ir.set_do_images([self.component])
        # Setup logger - we do not care about output, only errors
        logger = c_logger if c_logger else create_logger(sys.stderr,
                                                         logging.ERROR)
        self.ir._setup_logger(user_logger=logger)

    def tearDown(self):
        os.chdir(self.cwd)
        self.ir.clear_cache()


class PrinterBase(TestCaseBase):

    @property
    def print_value(self):
        return sys.stdout.getvalue()

    @classmethod
    def setUpClass(cls):
        # Use StringIO instead of stdout, we do not care about stderr here
        cls.stdout, sys.stdout = sys.stdout, StringIO()
        sys.stdout.name = "printer-test"

    @classmethod
    def tearDownClass(cls):
        sys.stdout = cls.stdout

    def setUp(self):
        # The logger writes everything into a StringIO object - see setUpClass
        super(PrinterBase, self).setUp(c_logger=create_logger(sys.stdout,
                                                              logging.INFO))
