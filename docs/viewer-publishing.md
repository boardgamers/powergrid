# Publishing the viewer

Upload `powergrid-viewer.umd.min.js`, `powergrid-viewer.css`, all `powergrid-viewer.umd.min.geography-*.js`, and all `powergrid-viewer.umd.min.locale-*.js` files from `viewer/dist`. The other UMD/CommonJS variants are not needed.

All files in a release must share one BGS `bundle` directory, with their relative paths preserved. Upload everything before saving the new entry URL. A main-JS-only upload will break language or asset loading. Keep engines and test data out of the viewer upload.

BGS compresses JS, CSS, JSON and WASM automatically during upload. Send the original bytes; do not create `.gz` files. Keep sourcemaps local unless you deliberately want to publish them. Set `viewer.scriptBytes` to the original entry size so BGS can show download progress.

The BGS admin's **Upload folder** control handles multi-file builds. For scripted releases, use BGS's `scripts/publish-viewer.mjs` with `--dir`, `--entry` and `--style`; it verifies every uploaded file, records the previous viewer, and activates only with `--apply --activate`. The full command and API contract are in the [BGS viewer documentation](https://docs.boardgamers.space/guide/viewer-api#publishing-a-viewer-with-multiple-files).

English needs no language download; other languages load when selected. Geographic SVG data loads as an optional chunk for the current map. Test a cold load, geographic backdrop, and a language change after publishing. Also check the browser Network panel for missing relative assets.
