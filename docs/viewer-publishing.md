# Publishing the viewer

Upload `powergrid-viewer.umd.min.js`, `powergrid-viewer.css`, all `powergrid-viewer.umd.min.geography-*.js`, and all `powergrid-viewer.umd.min.locale-*.js` files from `viewer/dist`. The other UMD/CommonJS variants are not needed.

All files in a release must share one BGS `bundle` directory, with their relative paths preserved. Upload everything before saving the new entry URL. A main-JS-only upload will break language or asset loading. Keep engines and test data out of the viewer upload.

BGS compresses JS, CSS, JSON and WASM automatically during upload. Send the original bytes; do not create `.gz` files. Keep sourcemaps local unless you deliberately want to publish them. Set `viewer.scriptBytes` to the original entry size so BGS can show download progress.

The BGS admin's **Upload folder** control handles multi-file builds. For scripted releases, use BGS's `scripts/publish-viewer.mjs` with `--dir`, `--entry` and `--style`; it verifies every uploaded file, records the previous viewer, and activates only with `--apply --activate`. The full command and API contract are in the [BGS viewer documentation](https://docs.boardgamers.space/guide/viewer-api#publishing-a-viewer-with-multiple-files).

English needs no language download; other languages load when selected. Geographic SVG data loads as an optional chunk for the current map. Test a cold load, geographic backdrop, and a language change after publishing. Also check the browser Network panel for missing relative assets.

The adaptive board viewer replaces the help toggle with `showUnselectedRegions`.
When deploying it, replace the obsolete `disableHelp` entry in the BGS game-version
preferences with `{ "name": "showUnselectedRegions", "label": "Show unselected regions", "type": "checkbox", "default": true }`.
Preserve the other preferences. BGS only persists declared preference names, so
this metadata change must accompany the viewer release. Old saved `disableHelp`
values are ignored by the viewer; move indicators are always enabled.

Viewer 2.3.19 also removes the `undoWholeTurn` and `fitToScreen` preferences.
Remove those two entries from the BGS game-version preferences, preserving all
other entries. Local undo now always removes one unconfirmed action, and board
sizing is always automatic; old saved values for these preferences are ignored.
The phase control pairs a phase pictogram with a skip, finish or edit pictogram.
From viewer 2.3.20, the paired pictograms use one shared grey surface with the
same silver/white-border hover as the color-blind and simulation controls. The
separator darkens on hover to preserve contrast. Passing has a normal black
border unless it is the only legal option, when it gets a blue cue. Unaffordable
plants are muted while choosing; the market outline is hidden when there are no
legal plant choices. The resource action shows skip until a purchase is made,
then finish; undoing all purchases restores skip. Phase actions and Undo share
2-unit borders while enabled and 1-unit borders while disabled. Local tentative
previews preserve public deck counters so buying resources does not flash an empty
draw pile. Existing pass-confirmation dialogs are unchanged.

Viewer 2.3.21 extends skip/finish behaviour to building and powering: skip before
any city is built or plant activated, finish afterwards, and skip again if all
those actions are undone. Skip only receives a blue cue when no legal action is
available. Button pictograms stay black on light hover backgrounds. Clickable
plants use their own border for the white hover cue, retaining the original
4-unit highlighted and 3-unit activated border widths and original blue.

Viewer 2.3.22 adds the remaining-card count centered on the draw pile's top card.
It uses the public deck count and remains stable during resource purchases and undo.

After packaging, run `node viewer/scripts/action-controls-smoke.mjs` to check
normal/only-pass states, hover/focus styling against the board-option buttons,
resource/building/powering transitions, and plant borders.
