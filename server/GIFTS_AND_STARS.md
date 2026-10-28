# HaslGram Stars and gifts — backend checklist

Android branding and automatic login do **not** provision in-app currency or gift inventory. The server is the sole source of truth for balances, ownership, Premium expiry and upgrades.

## Requested first-login defaults

The `haslgram-economy.env.example` template specifies:

- `TELESRV_STARS_STARTING_GRANT=2000` — one-time idempotent grant handled by the server; never show a locally invented 2000.
- `TELESRV_PREMIUM_GRANT_MONTHS=0` — no promotional Premium on new registration.

These names exist in the public OwpenGram server configuration as of this patch, but the real HaslGram deployment and its current config **have not been inspected or changed**.

**Important:** the documented Stars grant is lazy and can also affect existing accounts which have not yet received a grant. To restrict credit strictly to newly created accounts, add a server-side eligibility rule keyed to the account creation time before enabling it.

## Gifts: original, purchased first, upgraded separately

1. Check what gifting and `payments.getStarGifts` APIs the deployed server actually supports; enable compatible catalog, owned-inventory and purchase RPCs.
2. Catalog must offer **ordinary** (`not upgraded`) gifts on first purchase. Do not automatically mint collectible/unique attributes or prepay `include_upgrade`.
3. `payments.getPaymentForm(inputInvoiceStarGift)` purchases ordinary gifts and updates the server ledger atomically.
4. Later, on an explicit user choice, `payments.getStarGiftUpgradePreview`, payment for an upgrade, and `payments.upgradeStarGift` produce a collectible, with a server-confirmed unique ID, traits and ownership.
5. Android already contains Telegram-like gift UI code, but the chosen server must return the right media, preview attributes and payment updates. The resulting upgraded animation should play from the actual returned Lottie/TGS or video assets rather than from fake local UI state.
6. If importing official Telegram gift media through a `giftfetch` snapshot, independently verify ownership and redistribution rights first. Otherwise create licensed, original HaslGram gift artwork that preserves the same simple-gift-to-collectible user experience.
7. Test an ordinary purchase with 2000 Stars, restart the app to confirm balance/inventory, upgrade explicitly and test the animation, restart again, confirm one debit and persistent ownership.

**Never** copy a user’s actual Telegram Stars or owned Telegram gifts to HaslGram or present the two economies as interchangeable.

Source for server settings: https://github.com/owpengram/owpengram-server/blob/main/docs/configuration.en.md
Telegram gift flow reference: https://core.telegram.org/api/gifts
