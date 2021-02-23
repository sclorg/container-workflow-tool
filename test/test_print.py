import unittest

from test.common import PrinterBase


class RebuilderPrinterTestCase(PrinterBase):
    def test_config_contents(self):
        self.ir.show_config_contents()
        self.assertIn('python3', self.print_value)


if __name__ == '__main__':
    unittest.main()
