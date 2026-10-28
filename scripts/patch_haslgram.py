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
import re
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
    ap.add_argument("--server-info", required=True, type=Path)
    args = ap.parse_args()
    root = args.source
    key = read_and_verify_public_key(args.server_info)

    props_file = root / "gradle.properties"
    props = props_file.read_text(encoding="utf-8")
    for name, value in {
        "APP_PACKAGE": "com.haslgram.messenger",
        "RELEASE_STORE_PASSWORD": "HaslGramDebug_123",
        "RELEASE_KEY_ALIAS": "haslgramdebug",
        "RELEASE_KEY_PASSWORD": "HaslGramDebug_123",
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
    picker_file.write_text(picker, encoding="utf-8")

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
