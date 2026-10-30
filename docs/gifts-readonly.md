# HaslGram official-source gifts — Android read-only stage

This change applies to **hanxww/HaslGram-Android** only. The repo remains
a reproducible overlay on pinned OwpenGram Android source.

## In-app behavior

The main chat menu gets **«Подарки HaslGram»**. This opens a native
RecyclerView screen that fetches:

- \`https://api.haslgram.site/gifts/v1/catalog.json\`
- \`https://api.haslgram.site/gifts/v1/media/{telegram_document_id}.tgs\`

TGS files are downloaded lazily over HTTPS, SHA-256 checked against the
catalog, cached in the app's private cache and displayed through the existing
Telegram RLottie renderer. Bad IDs, paths, hashes, or unexpected
\`purchasable_in_haslgram=true\` are rejected.

The screen labels prices **Telegram Stars** (not Hasl Stars), and availability
as of the captured Telegram snapshot, **not live inventory**. Filters show
all types, non-sold-out types at snapshot, and types with reported upgrade
support. No buy, transfer or upgrade button is present.

The build overlays \`HaslGramGiftsFragment.java\` into
\`TMessagesProj/src/main/java/org/telegram/ui\` and inserts a main-dialog
menu entry. On unexpected upstream changes the overlay fails closed.

## Verify

- \`python3 -m unittest discover -s scripts/tests -v\`
- Build with the existing GitHub Actions \`HaslGram Android APK\` workflow
- In the debug APK open chats → menu → **Подарки HaslGram**
- Confirm 151 items from the currently hosted source snapshot and a TGS
  animation in visible rows; scroll and switch all three filters
- With network disabled, check retry messaging and that the client does
  not crash

## Important limitations

- This is a **read-only catalog**; neither \`economy.gift_catalog\` nor the
  spending, ownership, and upgrade paths are integrated.
- It does not display collectible model/pattern/backdrop media yet.
- The HTTP catalog describes historical availability only; it must never
  be presented as HaslGram sellable stock.
- No server tokens or Telegram authorization files are embedded.
- This change does not audit or solve other upstream client network traffic.
- Review rights/licensing before public redistribution of official Telegram
  animated assets. Retain GPL source and attribution for Android changes.
