import unittest

from django_rea.spi import ModelProvider


class ModelProviderSpiUnittest(unittest.TestCase):
    def test_duplicate_implementation(self):
        """
        Tests no duplicate implementations are allowed per interface.
        """
        ModelProvider.register_implementation(object, object)
        with self.assertRaises(ValueError) as context:
            ModelProvider.register_implementation(object, object)

        self.assertTrue(context.exception, 'The exception because duplicate was not thrown')
