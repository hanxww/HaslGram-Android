#!/usr/bin/env python3
"""Patch a pinned OwpenGram Android checkout into a HaslGram test APK.

Runs in GitHub Actions. The RSA key is never trusted merely because it was
fetched over HTTP: its PKCS#1 DER SHA-256 must match the independently pinned
fingerprint from the working HaslGram Desktop configuration.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path

SERVER_HOST = "150.241.68.248"
SERVER_PORT = 2398
SERVER_DC = 2
EXPECTED_RSA_DER_SHA256 = (
    "74460173fe5cc4fe9bbe04ae5e222914e28de6ae100f20b7d0cf4fa7cf46dcc5"
)


def once(contents: str, old: str, new: str, label: str) -> str:
    found = contents.count(old)
    if found != 1:
        raise ValueError(f"{label}: expected one match, found {found}")
    return contents.replace(old, new, 1)


def replace_property(contents: str, name: str, value: str) -> str:
    result, count = re.subn(
        rf"(?m)^{re.escape(name)}=.*$",
        lambda _match: f"{name}={value}",
        contents,
    )
    if count != 1:
        raise ValueError(f"gradle.properties: {name} count={count}, expected 1")
    return result


def read_and_verify_public_key(info_path: Path) -> str:
    response = json.loads(info_path.read_text(encoding="utf-8"))
    dc_id = int(response.get("dc_id", 0))
    if dc_id != SERVER_DC:
        raise ValueError(f"Server DC mismatch: expected {SERVER_DC}, got {dc_id}")
    pem = response.get("rsa_public_key_pem", "")
    match = re.fullmatch(
        r"\s*-----BEGIN RSA PUBLIC KEY-----\s*"
        r"([A-Za-z0-9+/=\s]+)"
        r"-----END RSA PUBLIC KEY-----\s*",
        pem,
    )
    if not match:
        raise ValueError("Server info does not contain a PKCS#1 RSA public key PEM")
    rsa_der = base64.b64decode(re.sub(r"\s", "", match.group(1)), validate=True)
    digest = hashlib.sha256(rsa_der).hexdigest()
    if digest != EXPECTED_RSA_DER_SHA256:
        raise ValueError(
            "HaslGram RSA identity mismatch; refuse to build with an untrusted key. "
            f"Expected {EXPECTED_RSA_DER_SHA256}; got {digest}"
        )
    if len(rsa_der) < 256:
        raise ValueError("RSA DER key unexpectedly short")
    print(f"Verified pinned HaslGram RSA public key (SHA-256 DER): {digest}")
    return pem.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--server-info", type=Path)
    args = ap.parse_args()
    root = args.source
    info_path = args.server_info
    if info_path is None:
        url = f"http://{SERVER_HOST}:{SERVER_PORT}/owpengram/server-info"
        with urllib.request.urlopen(url, timeout=25) as response:
            server_info = response.read(1024 * 1024)
        info_path = Path("/tmp/haslgram-build-server-info.json")
        info_path.write_bytes(server_info)
    key = read_and_verify_public_key(info_path)
    ci_password = os.environ.get("HASLGRAM_CI_KEY_PASS")
    if not ci_password or len(ci_password) < 16:
        raise ValueError("HASLGRAM_CI_KEY_PASS must contain a random CI-only password")

    props_file = root / "gradle.properties"
    props = props_file.read_text(encoding="utf-8")
    for name, value in {
        "APP_PACKAGE": "com.haslgram.messenger",
        "RELEASE_STORE_PASSWORD": ci_password,
        "RELEASE_KEY_ALIAS": "haslgramdebug",
        "RELEASE_KEY_PASSWORD": ci_password,
        "org.gradle.jvmargs": "-Xmx3g -XX:MaxMetaspaceSize=768m",
        "org.gradle.parallel": "false",
    }.items():
        props = replace_property(props, name, value)
    props_file.write_text(props, encoding="utf-8")

    strings_dir = root / "TMessagesProj/src/main/res"
    count = 0
    for xml in strings_dir.glob("values*/strings.xml"):
        value = xml.read_text(encoding="utf-8")
        if "OwpenGram" in value:
            xml.write_text(value.replace("OwpenGram", "HaslGram"), encoding="utf-8")
            count += 1
    if count < 1:
        raise ValueError("No OwpenGram application strings were found")

    # The original Russian introduction still said Telegram even when the
    # app label was already changed. Do not rewrite license or source notices:
    # these are strictly user-facing welcome-page strings.
    intro = {
        "values": [
            "An independent messenger powered by our own network.",
            "Messages, groups and files in one familiar app.",
            "Connect with your community on HaslGram.",
            "Sign in by phone and a one-time confirmation code.",
            "More features are coming as we develop.",
            "Hasl Stars, Premium and gifts are in development.",
        ],
        "values-ru": [
            "Независимый мессенджер на собственной инфраструктуре.",
            "Личные сообщения, группы и файлы в одном приложении.",
            "Общайтесь с друзьями в сети HaslGram.",
            "Вход по номеру телефона и одноразовому коду.",
            "Новые возможности появляются постепенно.",
            "Hasl Stars, Premium и подарки находятся в разработке.",
        ],
    }
    for xml in strings_dir.glob("values*/strings.xml"):
        value = xml.read_text(encoding="utf-8")
        folder = xml.parent.name
        value, replacements = re.subn(
            r'(<string name="Page1Title">)[^<]*(</string>)',
            lambda m: m.group(1) + "HaslGram" + m.group(2),
            value,
        )
        if replacements != 1:
            raise ValueError(f"Missing first onboarding title in {xml}")
        if folder in intro:
            for index, copy in enumerate(intro[folder], 1):
                key = f"Page{index}Message"
                value, changed = re.subn(
                    rf'(<string name="{key}">)[^<]*(</string>)',
                    lambda m, copy=copy: m.group(1) + copy + m.group(2),
                    value,
                )
                if changed != 1:
                    raise ValueError(f"Missing {key} in {xml}")
        else:
            # Preserve other languages while removing Telegram as the name
            # of our app from the six intro-page descriptions.
            value = re.sub(
                r'(<string name="Page[1-6]Message">)([^<]*)(</string>)',
                lambda m: m.group(1) + m.group(2).replace("Telegram", "HaslGram") + m.group(3),
                value,
            )
        xml.write_text(value, encoding="utf-8")

    servers_file = root / "TMessagesProj/src/main/java/org/telegram/owpengram/OwpengramServers.java"
    servers = servers_file.read_text(encoding="utf-8")
    servers = once(servers, 'public static final String ID_OWPENGRAM = "owpengram";',
                   'public static final String ID_OWPENGRAM = "haslgram";',
                   "built-in server ID")
    servers = once(servers, 'private static final String DEFAULT_HOST = "152.89.254.50";',
                   f'private static final String DEFAULT_HOST = "{SERVER_HOST}";',
                   "server host")
    servers = once(servers, 's.name               = "OwpenGram";',
                   's.name               = "HaslGram";', "server name")
    servers = once(servers, 's.description        = "This is a test OwpenGram server.";',
                   's.description        = "Private HaslGram messenger network.";',
                   "server description")
    servers = once(servers, 's.mainDcId           = 1;',
                   f's.mainDcId           = {SERVER_DC};', "server DC")
    servers = once(servers, 'result.add(telegramServer());\n', '',
                   "hide Telegram server")
    servers = once(servers, 'result.addAll(loadCustomServers());\n', '',
                   "hide custom servers")
    servers = once(servers, 'applyBuiltinIdentity(s);\n', '',
                   "pin displayed HaslGram identity")
    servers = once(
        servers,
        'return getServerById(getServerIdForAccount(accountNum));',
        'return owpengramServer(); // HaslGram-only: route every account to the pinned server.',
        "enforce HaslGram account route",
    )
    servers = once(
        servers,
        'getPrefs().edit().putString(KEY_ACCOUNT_SERVER + accountNum, serverId).apply();',
        'getPrefs().edit().putString(KEY_ACCOUNT_SERVER + accountNum, ID_OWPENGRAM).apply();',
        "enforce HaslGram server assignment",
    )
    # Never allow a caller, deep link, or an older saved account to select an
    # alternate MTProto endpoint. Re-pin at the final Java -> native boundary.
    servers = once(
        servers,
        'if (server == null) return;',
        'server = owpengramServer(); // HaslGram-only: enforce pinned config at native boundary.',
        "enforce endpoint at native configuration boundary",
    )

    oldkey = re.search(
        r'    static final String OWPENGRAM_RSA_KEY =\s*.*?;\n'
        r'    // fingerprint == 0',
        servers, flags=re.DOTALL,
    )
    if oldkey is None:
        raise ValueError("Could not find original RSA key constant")
    newkey = (
        '    static final String OWPENGRAM_RSA_KEY = '
        + json.dumps(key)
        + ';\n    // fingerprint == 0'
    )
    servers = servers[:oldkey.start()] + newkey + servers[oldkey.end():]
    servers_file.write_text(servers, encoding="utf-8")

    picker_file = root / "TMessagesProj/src/main/java/org/telegram/ui/ServerSelectFragment.java"
    picker = picker_file.read_text(encoding="utf-8")
    picker = once(picker, 'rows.add("add");\n', '', "hide add-server button")
    picker = once(picker, 'actionBar.setTitle("Choose a server");',
                  'actionBar.setTitle("HaslGram");', "picker title")
    picker = once(picker, 'actionBar.setSubtitle("Pick where to sign in");',
                  'actionBar.setSubtitle("Connect to the HaslGram network");', "picker subtitle")
    picker = once(picker, '"Official servers" : "Custom servers"',
                  '"HaslGram network" : "Custom servers"',
                  "rename server list section")
    picker_file.write_text(picker, encoding="utf-8")

    # An owpg://addserver link must not reopen server onboarding even when
    # the server picker no longer contains the Add Server row.
    launch_file = root / "TMessagesProj/src/main/java/org/telegram/ui/LaunchActivity.java"
    launch = launch_file.read_text(encoding="utf-8")
    launch = once(
        launch,
        "handleOwpengramAddServerLink(data);",
        "/* HaslGram-only: external server enrollment is disabled. */",
        "disable add-server deep links",
    )
    launch = once(launch, ': "OwpenGram";', ': "HaslGram";',
                  "deep link account label")
    launch_file.write_text(launch, encoding="utf-8")

    # Avoid sending HaslGram users to an upstream Telegram update or store.
    vars_file = root / "TMessagesProj/src/main/java/org/telegram/messenger/BuildVars.java"
    vars = vars_file.read_text(encoding="utf-8")
    vars = once(vars, "public static boolean CHECK_UPDATES = true;",
                "public static boolean CHECK_UPDATES = false;",
                "disable upstream updates")
    vars = once(vars,
                'public static String PLAYSTORE_APP_URL = "https://play.google.com/store/apps/details?id=org.telegram.messenger";',
                'public static String PLAYSTORE_APP_URL = "https://haslgram.site";',
                "use HaslGram website")
    vars_file.write_text(vars, encoding="utf-8")

    app_gradle = root / "TMessagesProj_AppStandalone/build.gradle"
    ag = app_gradle.read_text(encoding="utf-8")
    ag = once(ag,
              'abiFilters "armeabi-v7a", "arm64-v8a", "x86", "x86_64"',
              'abiFilters "arm64-v8a"',
              "build ARM64 APK")
    app_gradle.write_text(ag, encoding="utf-8")

    print(
        "HaslGram patches applied: "
        f"com.haslgram.messenger, {SERVER_HOST}:{SERVER_PORT} DC{SERVER_DC}, "
        f"{count} locales, server-only selection."
    )
    print("This is a TEST build; full traffic audit is still required.")


if __name__ == "__main__":
    main()
