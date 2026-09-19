"""Tests for catalog metadata used by custom Kryntis training."""

import unittest
from kryntis.datasets.catalog import MODEL_CATALOG, get_trainable_profiles


class TestCatalog(unittest.TestCase):

    def test_catalog_profiles_are_custom_training_hints_only(self) -> None:
        """Every serving-model profile maps to one existing custom corpus domain."""
        profiles = get_trainable_profiles()
        self.assertEqual(profiles, MODEL_CATALOG)
        self.assertTrue(all(profile.training_domain in profile.recommended_domains for profile in profiles))
        self.assertTrue(all(profile.ollama_tag for profile in profiles))


if __name__ == "__main__":
    unittest.main()
