import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tools


class FakeControl:
    def __init__(self, control_type, name):
        self.element_info = type(
            "ElementInfo",
            (),
            {
                "control_type": control_type,
                "name": name,
                "automation_id": "",
                "element": type("UIElement", (), {"CurrentIsPassword": False})(),
            },
        )()
        self.clicks = 0
        self.entered_text = None

    def is_enabled(self):
        return True

    def click_input(self):
        self.clicks += 1

    def set_edit_text(self, text):
        self.entered_text = text

    def get_value(self):
        return self.entered_text


class FakeWindow:
    def __init__(self, controls):
        self._controls = controls

    def window_text(self):
        return "Test window"

    def descendants(self):
        return self._controls


class ToolApprovalTests(unittest.TestCase):
    def test_denied_click_does_not_activate_control(self):
        button = FakeControl("Button", "Save")
        with patch("tools._resolve_window", return_value=FakeWindow([button])):
            result = tools.click_ui_element(
                "Test window", "Save", confirm=lambda description: False
            )

        self.assertFalse(result["ok"])
        self.assertEqual(button.clicks, 0)

    def test_denied_text_entry_does_not_change_field(self):
        field = FakeControl("Edit", "Search")
        with patch("tools._resolve_window", return_value=FakeWindow([field])):
            result = tools.type_into_field(
                "Test window", 1, "private text", confirm=lambda description: False
            )

        self.assertFalse(result["ok"])
        self.assertIsNone(field.entered_text)

    def test_approved_text_entry_is_verified(self):
        field = FakeControl("Edit", "Search")
        with patch("tools._resolve_window", return_value=FakeWindow([field])):
            result = tools.type_into_field(
                "Test window", 1, "query", confirm=lambda description: True
            )

        self.assertTrue(result["ok"])
        self.assertEqual(field.entered_text, "query")

    def test_ollama_diagnostics_tool_is_registered_and_dispatched(self):
        self.assertIn("ollama_diagnostics", [
            item["function"]["name"] for item in tools.TOOL_DEFINITIONS
        ])
        with patch("tools.ollama_diagnostics", return_value={"ok": True}) as check:
            result = tools.execute("ollama_diagnostics", {})
        check.assert_called_once_with()
        self.assertTrue(result["ok"])

    def test_password_field_is_never_modified(self):
        field = FakeControl("Edit", "Password")
        field.element_info.element.CurrentIsPassword = True
        with patch("tools._resolve_window", return_value=FakeWindow([field])):
            with self.assertRaisesRegex(ValueError, "password"):
                tools.type_into_field(
                    "Test window", 1, "secret", confirm=lambda description: True
                )

        self.assertIsNone(field.entered_text)

    def test_credential_named_field_is_never_modified(self):
        field = FakeControl("Edit", "API key")
        with patch("tools._resolve_window", return_value=FakeWindow([field])):
            with self.assertRaisesRegex(ValueError, "credential-related"):
                tools.type_into_field(
                    "Test window", 1, "secret", confirm=lambda description: True
                )

        self.assertIsNone(field.entered_text)


if __name__ == "__main__":
    unittest.main()
