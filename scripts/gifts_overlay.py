"""Install HaslGram's read-only official-gifts UI into a pinned Android checkout.

The overlay intentionally fails closed if the upstream menu source changes. No
upstream Telegram purchases, MTProto gifts or Star balance code is modified.
"""
from pathlib import Path
import shutil

MENU_ANCHOR = '''        io.add(R.drawable.outline_saved_24, getString(R.string.SavedMessages), () -> {
            Bundle args = new Bundle();
            args.putLong("user_id", UserConfig.getInstance(currentAccount).getClientUserId());
            presentFragment(new ChatActivity(args));
        });
'''
MENU_ADDITION = '''        io.add(R.drawable.outline_saved_24, "Подарки HaslGram", () -> {
            presentFragment(new HaslGramGiftsFragment());
        });
'''


def apply_gifts_overlay(android_source: Path) -> None:
    source = Path(__file__).resolve().parent / "haslgram_gifts" / "HaslGramGiftsFragment.java"
    if not source.is_file():
        raise RuntimeError("Missing HaslGram gift screen source")
    java = source.read_text(encoding="utf-8")
    if "class HaslGramGiftsFragment extends BaseFragment" not in java:
        raise RuntimeError("Unexpected gift screen implementation")
    if "https://api.haslgram.site/gifts/v1/" not in java:
        raise RuntimeError("Unexpected gift catalog endpoint")

    ui = android_source / "TMessagesProj/src/main/java/org/telegram/ui"
    dialogs = ui / "DialogsActivity.java"
    current = dialogs.read_text(encoding="utf-8")
    if current.count(MENU_ANCHOR) != 1 or MENU_ADDITION in current:
        raise RuntimeError("Pinned upstream menu differs; gifts overlay not applied")

    target = ui / "HaslGramGiftsFragment.java"
    if target.exists():
        raise RuntimeError("Refusing to overwrite an existing gift screen")

    # Validate all expected conditions before editing any files.
    updated = current.replace(MENU_ANCHOR, MENU_ANCHOR + MENU_ADDITION, 1)
    shutil.copyfile(source, target)
    dialogs.write_text(updated, encoding="utf-8")
    print("Installed read-only official gifts screen and main-chat menu entry")
