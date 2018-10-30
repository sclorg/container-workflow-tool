import unittest
from test.common import TestCaseBase


class BrewTestCase(TestCaseBase):
    def setUp(self):
        super(BrewTestCase, self).setUp()
        self.component = 'postgresql'
        self.nvr = 'postgresql-0-1.f26container'
        self.ir.set_do_images([self.component])
        self.ir._setup_brewapi()

    def test_setup_brewapi(self):
        # First, setup ImageRebuilder without setting up brewapi
        super(BrewTestCase, self).setUp()
        self.assertEqual(self.ir.brewapi, None)
        self.ir._setup_brewapi()
        self.assertNotEqual(self.ir.brewapi, None)

    def test_get_nvr(self):
        nvr = self.ir.brewapi.get_nvr('f26-container', self.component)
        self.assertIn(self.nvr, nvr)

    def test_get_buildinfo(self):
        buildinfo = self.ir.brewapi.get_buildinfo(self.nvr)
        self.assertIn('build_id', buildinfo)
        self.assertEqual(buildinfo['build_id'], 1018414)

    def test_get_taskinfo(self):
        taskinfo = self.ir.brewapi.get_taskinfo(24268996)
        self.assertIn('create_ts', taskinfo)
        self.assertEqual(taskinfo['create_ts'], 1516286326.9219)


if __name__ == '__main__':
    unittest.main()
