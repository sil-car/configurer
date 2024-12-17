import unittest
from src.configurer import reg


class TestKeyPath(unittest.TestCase):
    def test_root(self):
        kp = reg.KeyPath('HKEY_LOCAL_USER\\Software\\Windows')
        self.assertEqual(kp.base_key, 'HKEY_LOCAL_USER')
        self.assertEqual(kp.name, 'Windows')
        self.assertEqual(str(kp.parent), 'HKEY_LOCAL_USER\\Software')
        self.assertEqual(kp.key_path, 'Software\\Windows')