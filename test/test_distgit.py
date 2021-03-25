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
        self.ir.conf["from_tag"] = "test"
        self.ir.dist_git_changes()
        tmp = self.ir._get_tmp_workdir()
        dpath = os.path.join(tmp, self.component, 'Dockerfile')
        self.assertTrue(os.path.isfile(dpath))
        tag_found = False
        with open(dpath) as f:
            if ":test" in f.read():
                tag_found = True
        self.assertTrue(tag_found)

    def test_distgit_commit_msg(self):
        msg = "Unit testing"
        self.ir.set_commit_msg(msg)
        self.assertEqual(self.ir.distgit.commit_msg, msg)

    def test_tag_dockerfile(self):
        self.ir.conf["from_tag"] = "test"
        self.ir.dist_git_changes()
        tmp = self.ir._get_tmp_workdir()
        cpath = os.path.join(tmp, self.component)
        dpath = os.path.join(cpath, 'Dockerfile')
        found_tag = False
        with open(dpath) as f:
            if ":test" in f.read():
                found_tag = True
        self.assertTrue(found_tag)


if __name__ == '__main__':
    unittest.main()
