from __future__ import annotations

import unittest

from sessgraph import (
    DuplicateToolError,
    SyncToolExecutor,
    ToolNotFoundError,
    ToolRegistry,
    ToolResult,
    ToolSpec,
    ValidationError,
)


class ToolTests(unittest.TestCase):
    def test_registry_registers_and_lists_tools(self) -> None:
        registry = ToolRegistry()
        spec = ToolSpec(
            name="echo",
            description="Echo text.",
            handler=lambda arguments: {"text": arguments["text"]},
            metadata={"scope": "test"},
        )

        registered = registry.register(spec)

        self.assertEqual(registered, spec)
        self.assertEqual(registry.get("echo"), spec)
        self.assertEqual(registry.list_tools(), (spec,))
        with self.assertRaises(TypeError):
            spec.metadata["new"] = "blocked"

    def test_registry_rejects_duplicate_and_unknown_tools(self) -> None:
        registry = ToolRegistry()
        spec = ToolSpec(name="echo", description="Echo text.", handler=lambda arguments: {})
        registry.register(spec)

        with self.assertRaises(DuplicateToolError):
            registry.register(spec)

        with self.assertRaises(ToolNotFoundError):
            registry.get("missing")

    def test_tool_spec_validates_name_description_handler_and_metadata(self) -> None:
        with self.assertRaises(ValidationError):
            ToolSpec(name="", description="Bad.", handler=lambda arguments: {})

        with self.assertRaises(ValidationError):
            ToolSpec(name="bad", description="", handler=lambda arguments: {})

        with self.assertRaises(ValidationError):
            ToolSpec(name="bad", description="Bad.", handler="not-callable")

        with self.assertRaises(ValidationError):
            ToolSpec(name="bad", description="Bad.", handler=lambda arguments: {}, metadata=[])

    def test_sync_executor_returns_success_result(self) -> None:
        registry = ToolRegistry()
        registry.register(
            ToolSpec(
                name="add",
                description="Add two integers.",
                handler=lambda arguments: {"value": arguments["a"] + arguments["b"]},
            )
        )
        executor = SyncToolExecutor(registry)

        result = executor.execute("add", {"a": 2, "b": 3})

        self.assertEqual(result, ToolResult(tool_name="add", ok=True, output={"value": 5}))
        self.assertEqual(result.to_dict(), {
            "tool_name": "add",
            "ok": True,
            "output": {"value": 5},
            "error": None,
        })

    def test_tool_result_validates_ok_error_consistency(self) -> None:
        with self.assertRaises(ValidationError):
            ToolResult(tool_name="bad", ok=True, error="should not be set")

        with self.assertRaises(ValidationError):
            ToolResult(tool_name="bad", ok=False)

    def test_sync_executor_returns_failure_result_for_handler_error(self) -> None:
        def fail(_arguments: object) -> object:
            raise RuntimeError("boom")

        registry = ToolRegistry()
        registry.register(ToolSpec(name="fail", description="Fail.", handler=fail))
        executor = SyncToolExecutor(registry)

        result = executor.execute("fail", {})

        self.assertFalse(result.ok)
        self.assertEqual(result.tool_name, "fail")
        self.assertEqual(result.output, {})
        self.assertEqual(result.error, "boom")

    def test_sync_executor_rejects_unknown_tool_and_non_json_output(self) -> None:
        registry = ToolRegistry()
        executor = SyncToolExecutor(registry)

        with self.assertRaises(ToolNotFoundError):
            executor.execute("missing", {})

        registry.register(ToolSpec(name="bad", description="Bad.", handler=lambda _args: []))
        result = executor.execute("bad", {})
        self.assertFalse(result.ok)
        self.assertIn("output must be a JSON object", result.error)


if __name__ == "__main__":
    unittest.main()
