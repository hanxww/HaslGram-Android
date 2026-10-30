# HaslGram Android

An independent Android client build for the **HaslGram** MTProto network.

## Build on GitHub

This repository contains the HaslGram-specific source patch and an Android
GitHub Actions build workflow. The workflow checks out a **pinned upstream**
[OwpenGram Android](https://github.com/owpengram/owpengram-android-client)
commit (GPL-2.0-or-later), validates the HaslGram server RSA identity,
applies the patch and builds a debug APK. Android Studio is not required locally.

- Android package: `com.haslgram.messenger`
- Network: `150.241.68.248:2398`, MTProto main DC `2`
- Server identity: RSA PKCS#1 DER SHA-256 pinned in `scripts/patch_haslgram.py`
- Build variant: `:TMessagesProj_AppStandalone:assembleAfatDebug`
- ABI: `arm64-v8a`
- APK: **Actions → HaslGram Android APK → Artifacts**
- Signing: **disposable test keystore generated per run**. These builds
  cannot upgrade each other. Do not distribute them as production releases.

This is a source-overlay repository: upstream source is cloned in each workflow
run; the complete upstream source is not copied into this Git repository.
The exact upstream commit is pinned in the workflow for reproducibility.

### Important limitations

This is an **early test build**. The server list and account routing are patched
to select HaslGram. It is not a completed network-isolation security audit:
there may be other Telegram endpoints, web links or services in the upstream
client which will need review before release. Similarly, paid features,
Hasl Stars, **gift purchases and upgrades**, Premium, virtual numbers and the
shop are not yet integrated into the Android UI. A **read-only** gift catalog
screen is being introduced: it shows Telegram-source historical gift metadata
and lazily plays SHA-256-verified TGS files from the HaslGram HTTPS endpoint.
It does not imply a Telegram gift is owned, currently on sale, or purchasable
with Hasl Stars. See [gifts UI details](docs/gifts-readonly.md).

The build reads `/owpengram/server-info` on the HaslGram MTProto endpoint.
It refuses to build unless the fetched RSA key matches the independently pinned
SHA-256 identity. **Do not update the fingerprint merely to make a failing
build green.** First independently verify the real server key.

## Attribution and license

OwpenGram Android derives from Telegram Android and is licensed under
**GNU GPL v2 or later**. Preserve copyright notices and provide the complete
corresponding source when distributing modified APKs. The pinned upstream
revision and this repository's patch are both part of the source for the
resulting APK. See the upstream `LICENSE` file.
