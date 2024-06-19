import unittest
from unittest.mock import MagicMock
from python_utils.flask.shared import SharedDataProxyDict


class TestSharedDataProxy(unittest.TestCase):
    def setUp(self):
        # Set up the mock for GlobalDataStore
        self.mock_store = MagicMock()
        self.proxy = SharedDataProxyDict(name="name", global_data_store=self.mock_store)

    def test_set_item(self):
        self.proxy['key1'] = {'inner_key': 'value'}
        self.mock_store.update.assert_called_with('name', {'key1': {'inner_key': 'value'}})

    def test_get_item(self):
        self.mock_store.get_data.return_value = {'key1': 'value'}
        result = self.proxy['key1']
        self.mock_store.get_data.assert_called()
        self.assertEqual(result, 'value')

    def test_len(self):
        self.mock_store.get_data.return_value = {'key1': 'value1', 'key2': 'value2'}
        self.assertEqual(len(self.proxy), 2)

    def test_iter(self):
        self.mock_store.get_data.return_value = {'key1': 'value1', 'key2': 'value2'}
        keys = list(iter(self.proxy))
        self.assertEqual(keys, ['key1', 'key2'])

    def test_repr(self):
        self.mock_store.get_data.return_value = {'key1': 'value1', 'key2': 'value2'}
        self.assertEqual(repr(self.proxy), "{'key1': 'value1', 'key2': 'value2'}")

    def test_contains(self):
        self.mock_store.get_data.return_value = {'key1': 'value1', 'key2': 'value2'}
        self.assertTrue('key1' in self.proxy)
        self.assertFalse('key3' in self.proxy)


if __name__ == '__main__':
    unittest.main()
