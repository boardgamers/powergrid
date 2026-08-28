// `Phase` comes from the package root (the built `dist`), never from
// `powergrid-engine/src/gamestate`: webpack 4 parses the engine SOURCE for the
// unit-test bundle and dies on its `??`. Game.vue can import the source because the
// app build does not; a file with a spec beside it cannot.
import type { GameState } from 'powergrid-engine';
import { Phase } from 'powergrid-engine';

/**
 * The order the player boards are stacked in (`Game.vue`'s `adjustedPlayerOrder`).
 *
 * Two different orders sit on this board and they are easy to confuse -- the issue
 * that produced this file (#141) was exactly that confusion:
 *
 *  - TABLE order: where a player sits. Fixed for the whole game. This is what the
 *    boards show when the preference is off, and it is why bidding "out of turn
 *    order" is usually not a bug at all.
 *  - TURN order (`G.playerOrder`): recomputed every round from cities and largest
 *    plant. The auction runs down it; resources and building run back UP it.
 *
 * Kept out of the component so it can be tested against a real engine state, the
 * same way `util/resource-rows.ts` is -- and because the component version could not
 * be tested at all, which is how it stayed wrong.
 *
 * Written without optional chaining: webpack 4 parses the unit-test bundle and
 * rejects `?.` (same note as `util/turn-buffer.ts`).
 */
export function playerOrderForDisplay(G: GameState | null | undefined, adjustPlayerOrder: boolean): number[] {
    if (!G) {
        return [];
    }

    if (!adjustPlayerOrder) {
        return G.players.map((_p, i) => i); // 0 1 2 3 ...
    }

    // Copy before reversing. `Array.reverse` works in place, so reading the order off
    // the state used to rewrite it -- see `player-order.spec.ts`. The engine already
    // spreads before it reverses, in both places it walks the order backwards.
    if (G.phase == Phase.Auction) {
        return [...G.playerOrder];
    }

    return [...G.playerOrder].reverse();
}
