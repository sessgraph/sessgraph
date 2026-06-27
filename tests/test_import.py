from __future__ import annotations

import unittest

import sessgraph


class ImportSmokeTests(unittest.TestCase):
    def test_public_package_imports_core_runtime_symbols(self) -> None:
        self.assertIn("AgentDefinition", sessgraph.__all__)
        self.assertIn("ActivationRunner", sessgraph.__all__)
        self.assertIn("InMemorySessionStore", sessgraph.__all__)
        self.assertIsNotNone(sessgraph.AgentDefinition)
        self.assertIsNotNone(sessgraph.ActivationRunner)


if __name__ == "__main__":
    unittest.main()
