"""Fail-closed tests for the HaslGram gift overlay (no Android SDK needed)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gifts_overlay import MENU_ANCHOR, MENU_ADDITION, apply_gifts_overlay


class GiftsOverlayTests(unittest.TestCase):
    def make_checkout(self, text):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        ui = root / "TMessagesProj/src/main/java/org/telegram/ui"
        ui.mkdir(parents=True)
        (ui / "DialogsActivity.java").write_text(text, encoding="utf-8")
        return temp, root, ui

    def test_apply_once(self):
        temp, root, ui = self.make_checkout("before\n" + MENU_ANCHOR + "after\n")
        try:
            apply_gifts_overlay(root)
            self.assertIn(MENU_ADDITION, (ui / "DialogsActivity.java").read_text())
            self.assertIn("class HaslGramGiftsFragment", (ui / "HaslGramGiftsFragment.java").read_text())
        finally:
            temp.cleanup()

    def test_missing_anchor_does_not_create_screen(self):
        temp, root, ui = self.make_checkout("changed upstream")
        try:
            with self.assertRaises(RuntimeError):
                apply_gifts_overlay(root)
            self.assertFalse((ui / "HaslGramGiftsFragment.java").exists())
            self.assertEqual((ui / "DialogsActivity.java").read_text(), "changed upstream")
        finally:
            temp.cleanup()

    def test_second_apply_rejected(self):
        temp, root, ui = self.make_checkout(MENU_ANCHOR)
        try:
            apply_gifts_overlay(root)
            with self.assertRaises(RuntimeError):
                apply_gifts_overlay(root)
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
