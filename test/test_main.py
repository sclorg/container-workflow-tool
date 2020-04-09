import unittest

from container_workflow_tool.utility import RebuilderError
from test.common import TestCaseBase


class RebuilderTestCase(TestCaseBase):

    def test_set_config(self):
        self.ir.set_config('f27.yaml', release='fedora27')
        self.assertEqual(self.ir.conf.releases["fedora"]["current"], '27')

    def test_do_images(self):
        self.ir.set_do_images('s2i-base')
        images = [i["component"] for i in self.ir._get_images()]
        self.assertIn('s2i-base', images)
        self.assertNotIn('nginx', images)

    def test_setup_tmp_workdir(self):
        self.ir.tmp_workdir = self.ir._get_tmp_workdir()
        self.assertNotEqual(self.ir.tmp_workdir, None)
        self.assertIn('Testing', self.ir.tmp_workdir)

    def test_get_existing_tmp_workdir(self):
        tmp = self.ir._get_tmp_workdir()
        tmp2 = self.ir._get_tmp_workdir()
        self.assertEqual(tmp, tmp2)
        self.ir.tmp_workdir = tmp

    def test_do_not_setup_workdir(self):
        self.ir.tmp_workdir = self.ir._get_tmp_workdir(setup_dir=False)
        self.assertEqual(self.ir.tmp_workdir, None)

    def test_set_workdir(self):
        with self.assertRaises(RebuilderError):
            self.ir.set_tmp_workdir('/tmp/nonexisting')
        tmp_path = '/tmp'
        self.ir.set_tmp_workdir(tmp_path)
        self.assertEqual(self.ir.tmp_workdir, tmp_path)
        # Do not delete /tmp
        self.ir.tmp_workdir = None

    def test_get_set_workdir(self):
        tmp_path = '/tmp'
        self.ir.set_tmp_workdir(tmp_path)
        tmp = self.ir._get_tmp_workdir()
        self.assertEqual(tmp, tmp_path)
        # Do not delete /tmp
        self.ir.tmp_workdir = None

    def test_set_repo_url(self):
        url = 'url'
        self.ir.set_repo_url(url)
        self.assertEqual(self.ir.repo_url, url)


if __name__ == '__main__':
    unittest.main()
