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
Hasl Stars, gifts, Premium, virtual numbers and the shop are not yet integrated
into the Android UI.

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


## HaslGram branding (next Android test build)

The overlay now includes the HaslGram channel/app icon as
`branding/haslgram-icon.webp`. `scripts/brand_assets.py` generates the
launcher icon at every Android density, round and adaptive icon foregrounds,
upstream alternative-icon assets, onboarding/server-selector logo, and
Android 12 splash image. The `patch_haslgram.py` overlay also replaces
onboarding branding and Russian/English welcome copy. Copyright notices and
source-code class names from the GPL upstream stay intact.

Every build verifies the Android package and **HaslGram** application label.
Review the `HaslGram-Android-arm64-branded-test` artifact from a successful
GitHub Actions run. This is a test APK with a one-time signing key; it is
not in-place upgradeable over earlier HaslGram debug APKs signed using
different keys. Uninstall the old debug build first **only after backing up
anything important in it**; uninstalling deletes the app's local data.

**Scope:** Branded home-screen icons, splash, introductory screens and
server selection. This does **not** claim that every inherited Telegram
feature, link or network integration has been audited. Full independence
still requires on-device network testing and replacement/removal of any
remaining upstream-only features.

## HaslGram onboarding and economy (next test build)

- **Direct login:** a fresh install opens phone registration immediately. The
  HaslGram MTProto endpoint/key is pinned and applied automatically during
  startup. No server chooser and no **Join** button are required. The intro
  screen's legacy entry and the add-account path also bypass the server picker.
- **Hasl Stars branding:** the UI uses the Hasl Stars name for the upstream
  Telegram Stars user-facing strings. It does not forge local balance values.
- **Starter balance / Premium:** the deployment template in
  `server/haslgram-economy.env.example` proposes a one-time 2000-Stars grant
  and zero complimentary Premium months. **These settings are not live until
  deliberately applied to the real HaslGram MTProto server.**
- **Gifts:** the Android upstream already has gift purchase, collectible
  upgrade and Lottie animation UI. A real, compatible **server-side** catalog,
  payment/upgrade RPC implementation, and licensed media assets are required
  to make the requested normal-gift-then-paid-upgrade experience operational.
  See `server/GIFTS_AND_STARS.md`. No gift catalog is fabricated in the APK.

The first-launch change must still be verified on an actual Android device
before treating the new APK as ready for production. An account's existing
local data and keystore signature should be backed up before changing test APKs.
