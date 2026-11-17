# Auction auto-pass

Public-money games automatically pass players who cannot afford the next legal bid.
With hidden money, each player can enable `autoPassBids`; it defaults to false. The
setting is private, but the timing of a pass can reveal insufficient money, as the
control's tooltip explains. The engine performs the passes even if the player is
offline. The setting applies after the next committed move, not inside the host's
settings-only persistence endpoint.

This covers normal and sealed auctions, and skipping a nomination when no plant is
affordable. Exact-minimum sealed bids and Recharged's 1-Elektro discount remain
available. Mandatory first-round purchases and plant/resource discards are never
skipped. Automatic passes use normal move logs (hidden until resolution for sealed
bids), timestamps and time increments. Historical replay does not re-evaluate
today's settings or insert new passes.

## Resources and Building

Resources and Building also auto-pass when Pass is the only legal action. With
public money this is automatic. With hidden money, inability to act even with
unlimited money is public information and needs no opt-in (for example, no usable
fuel storage, empty supply, or nowhere legal to build). When only affordability
prevents acting, the private `autoPassResources` or `autoPassBuilding` setting must
be enabled. Both default to false and take effect after the next committed move.

The player-card checkbox follows the current phase. Existing settings are retained
when toggling another phase's setting. Analysis stays manual; tentative purchases
and builds remain undoable and are never automatically confirmed. Queued plans
run before automatic passes. Ordinary Pass logs, clocks and replay are preserved.

Published on BGS v13 with engine **2.0.37** and viewer **2.3.32**. The two new
checkbox declarations from `scripts/player-settings.json` were merged into the
BGS game settings alongside `autoPassBids`, preserving unrelated settings and
viewer preferences. All three labels name their current phase, are translated
in all 17 languages and fit left-aligned within the existing reserved row.
See [the release record](releases/phase-auto-pass-2.0.37-2.3.32.json) for public
asset hashes and verification.

Use `/?mode=fuel-hidden` or `/?mode=city-hidden` to let Ada take the last affordable
option. Reset and compare with the checkbox enabled or the public-money scenarios.
`/?mode=fuel-hidden-impossible` demonstrates a publicly empty oil market being
skipped even when the hidden-money checkbox is off.

## Preview and existing auction release

Preview: build the engine and viewer, then run
`node viewer/scripts/auction-preview.mjs` (default port 5216). The scenario selector
offers public/hidden money and normal/sealed bidding. In the hidden-money preview,
toggle the checkbox in your player card before pressing **Ada bids 10**.
`/mobile` embeds the same interactive preview at phone width.

Published on BGS with engine 2.0.19 and viewer 2.3.15. Asset URLs and hashes are in
[the release record](releases/auction-auto-pass-2.3.15.json). The declaration in
`scripts/player-settings.json` is merged into BGS’s game `settings` list (not viewer
preferences). Preserve other declared settings in future releases. The control uses
the standard BGS `settings` / `update:setting` protocol, like Outpost.
