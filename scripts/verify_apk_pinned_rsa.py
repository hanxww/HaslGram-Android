#!/usr/bin/env python3
"""Fail a HaslGram release when the compiled APK lacks the pinned RSA key."""
import argparse
import base64
import hashlib
import re
import zipfile

EXPECTED = "74460173fe5cc4fe9bbe04ae5e222914e28de6ae100f20b7d0cf4fa7cf46dcc5"
PEM = re.compile(rb"-----BEGIN RSA PUBLIC KEY-----\n(?:[A-Za-z0-9+/=]+\n)+-----END RSA PUBLIC KEY-----")

def verify(apk):
    found = set()
    with zipfile.ZipFile(apk) as archive:
        dexfiles = [n for n in archive.namelist() if re.fullmatch(r"classes\d*\.dex", n)]
        if not dexfiles:
            raise ValueError("APK contains no classes.dex")
        for name in dexfiles:
            for match in PEM.finditer(archive.read(name)):
                lines = match.group().splitlines()
                der = base64.b64decode(b"".join(lines[1:-1]), validate=True)
                found.add(hashlib.sha256(der).hexdigest())
    if EXPECTED not in found:
        raise ValueError(
            "Compiled APK has NO pinned HaslGram public RSA key! "
            "Found other RSA DER digests: " + ", ".join(sorted(found))
        )
    print("PASS: APK contains pinned HaslGram RSA key SHA256 " + EXPECTED)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("apk")
    args = parser.parse_args()
    verify(args.apk)
