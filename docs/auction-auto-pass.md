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
