import unittest
import os

from test.common import TestCaseBase


class DistgitTestCase(TestCaseBase):
    def setUp(self):
        super(DistgitTestCase, self).setUp()
        self.ir._setup_distgit()

    def test_setup_distgit(self):
        super(DistgitTestCase, self).setUp()
        self.assertEqual(self.ir.distgit, None)
        self.ir._setup_distgit()
        self.assertNotEqual(self.ir.distgit, None)

    def test_pull_downstream(self):
        self.ir.pull_downstream()
        tmp = self.ir._get_tmp_workdir()
        cpath = os.path.join(tmp, self.component)
        self.assertTrue(os.path.isdir(cpath))
        dpath = os.path.join(cpath, 'Dockerfile')
        self.assertTrue(os.path.isfile(dpath))

    def test_pull_upstream(self):
        self.ir.pull_upstream()
        tmp = self.ir._get_tmp_workdir()
        cpath = os.path.join(tmp, 's2i')
        self.assertTrue(os.path.isdir(cpath))
        dpath = os.path.join(cpath, 'base', 'Dockerfile')
        self.assertTrue(os.path.isfile(dpath))

    def test_distgit_changes(self):
        self.ir.dist_git_changes()
        tmp = self.ir._get_tmp_workdir()
        cpath = os.path.join(tmp, self.component)
        self.assertTrue(os.path.isdir(cpath))
        dpath = os.path.join(cpath, 'Dockerfile')
        self.assertTrue(os.path.isfile(dpath))

    def test_distgit_commit_msg(self):
        msg = "Unit testing"
        self.ir.set_commit_msg(msg)
        self.assertEqual(self.ir.distgit.commit_msg, msg)


if __name__ == '__main__':
    unittest.main()
