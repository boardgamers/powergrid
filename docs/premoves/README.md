# Planning and premoves

The existing black status bar offers **Simulate** during auctions/resource buying and **Plan** once resource buying is finished. Both use the normal board controls. All money information stays on the player board, including the balance after projected income. The board’s Undo control allows trying another purchase or route; there is one plan, limited to the remaining phases of the current round.

Plant bids are assumed winning prices in the simulation. Resource purchases use today's prices and storage limits. Neither can be queued. The preview does not predict other players' decisions or hidden plant draws, so building leaves the plant market and public deck indicator unchanged. Final scoring uses available power capacity without awarding normal income. Australia’s uranium mine sales are excluded from projected city income because their price depends on other players' sales.

After real resource buying, finish a simulated building and/or powering phase with **Done**, then select **Validate**. Each queued phase includes its ending pass. A phase already due plays immediately when validated; later phases wait for the player's turn. The Plan button shows the number of saved premoves and reopens them on the board, where Undo edits the preview and Cancel all clears the saved queue, including after reload, and execution does not require an open browser.

Each city keeps its exact previewed price. The server rechecks every action against the current position, and commits a phase only if all its moves are legal. An occupied/unaffordable city, a changed price, or missing fuel stops the queue without partially spending on that phase. Already completed phases remain played. Manual moves replace the queue for that phase; later queued phases remain. Queues expire at the round boundary or game end.

Queue edits use revision checks and request IDs, are visible only to their owner, and use the existing `canMoveOutOfTurn`/`isLiveUpdate` hooks. Executed actions use normal engine rules and commit boundaries. `timeIncrements` credits execution, not simulation or queue edits. No protocol package change is needed.

## Local preview

From the repository root:

```sh
npm --prefix engine run build
NODE_OPTIONS=--openssl-legacy-provider npm --prefix viewer run package
node viewer/scripts/premove-preview.mjs
```

Open <http://127.0.0.1:5204/>. The green preview toolbar selects prepared positions after resource buying, after city building, at an auction, or during resource buying. **Finish next opponent phase** advances the other players so you can see premoves execute. **Other player’s view** demonstrates that the queue is private. The server listens only on localhost and keeps its disposable games in memory.

## Verification

```sh
npm --prefix engine test
npm --prefix engine run lint
NODE_OPTIONS=--openssl-legacy-provider npm --prefix viewer run test:unit
npm --prefix viewer run test:tutorial
node viewer/scripts/premove-smoke.mjs
```

The browser smoke test runs the built viewer against the real engine wrapper, with no mocked components. It exercises normal board controls, checks that simulation sends no moves, verifies the budget against eventual execution, tests private queues/reload/cancellation, and covers auction assumptions and mobile powering. Set `CHROMIUM_PATH` to an installed Chromium executable if needed. Set `SCREENSHOT_DIR` to save screenshots of the same run.
