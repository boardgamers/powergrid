import { isEqual } from 'lodash';
import type { GameState, LogItem, LogMove, Move } from 'powergrid-engine';
import { move as engineMove } from 'powergrid-engine';

/**
 * Pure helpers for the viewer's tentative-turn buffer.
 *
 * The platform persists only COMMITTED states (engine `newTurn !== false`); a turn in
 * progress lives solely in the acting viewer's buffer, which is (re)sent whole on every
 * action and replayed server-side from the last committed state. These helpers decide
 * how an incoming state relates to that buffer and how to preview the buffer locally.
 */

/**
 * Should a state arriving on the `gamelog` channel be applied directly, rather than
 * refetched?
 *
 * Only while it is TENTATIVE. That is the single reason this channel exists: tentative
 * states are never persisted or broadcast, so the move response is the only way one can
 * reach the acting player's viewer.
 *
 * A committed state is refetched instead, exactly as it was before the tentative-turn
 * model. The same `gamelog` channel also carries the plain log fetch, and
 * `GET /gameplay/:id/log` is not logged-in: it resolves the player with `findIndex`,
 * which yields -1 when there is no user, and `stripSecret` then blanks EVERY player's
 * `availableMoves`. Adopting that state left the acting player looking at a fully
 * rendered board with nothing clickable after a page refresh, recovering only by
 * re-entering the game. `fetchState` asks a route that knows who is asking.
 */
export function shouldAdoptLogState(state?: GameState | null): boolean {
    // Written without optional chaining on purpose: webpack 4's parser rejects `?.` in
    // this module under the unit-test pipeline.
    return !!state && state.newTurn === false;
}

/**
 * Compare a move echoed in a log entry with a buffered one. The engine may annotate
 * the logged copy (`usedPlantDiscount`, `fromSupply`), so only the identity fields
 * count: name, payload, and the stamp given when the move entered the buffer.
 */
export function moveMatches(logged: Move, buffered?: Move): boolean {
    return (
        !!buffered &&
        logged.name === buffered.name &&
        logged.time === buffered.time &&
        isEqual(logged.data, buffered.data)
    );
}

/**
 * A tentative state is a valid preview only if it is the server's replay of exactly
 * the current turn buffer: the visible log must extend the committed log by precisely
 * the buffered moves, in order. (Tentative moves are always visible log entries —
 * fastBid bids go to the hidden log but commit immediately.) Anything else is a stale
 * echo — a response that raced a local undo or a newer move — and must be dropped.
 */
export function matchesTurnBuffer(
    state: GameState,
    committedState: GameState | null,
    turnMoves: Move[],
    player: number | undefined
): boolean {
    if (!committedState) {
        return false;
    }

    const committedLength = committedState.log.length;

    if (state.log.length !== committedLength + turnMoves.length) {
        return false;
    }

    return state.log
        .slice(committedLength)
        .every((item, i) => item.type === 'move' && item.player === player && moveMatches(item.move, turnMoves[i]));
}

/**
 * Adjust the turn buffer to an incoming COMMITTED state.
 *
 * - Our own commit echoed back: the new log contains the buffered moves — drop them
 *   (usually emptying the buffer; a racing extra move may survive if we can still act).
 * - Someone else's commit (simultaneous Bureaucracy): the new log contains no moves of
 *   ours — keep the whole buffer, to be replayed on the new base.
 * - Anything else (our turn superseded, e.g. auto-played after a drop, a leftover whose
 *   effect is already committed hidden — a fastBid bid — or a log that did not grow
 *   monotonically): scrap the buffer.
 */
export function rebaseTurnBuffer(
    committed: GameState,
    previousLog: LogItem[] | null,
    turnMoves: Move[],
    player: number | undefined
): Move[] {
    if (!previousLog || committed.log.length < previousLog.length) {
        return [];
    }

    const appendedOurs = committed.log
        .slice(previousLog.length)
        .filter((item) => item.type === 'move' && item.player === player)
        .map((item) => (item as LogMove).move);

    if (!appendedOurs.every((move, i) => moveMatches(move, turnMoves[i]))) {
        return [];
    }

    const remaining = turnMoves.slice(appendedOurs.length);

    // A leftover move is only replayable if we can still act on the new base. This is
    // how buffered moves whose effect is HIDDEN get dropped: a fastBid bid goes to the
    // engine's hidden log and commits immediately, so a chooser's [choose, bid] buffer
    // echoes back with only the choose visible — the bid is already reflected in the
    // committed state, and the mover has left `currentPlayers`. Scrap the rest
    // silently instead of letting the replay reject it with an error.
    if (remaining.length > 0 && (player === undefined || !committed.currentPlayers.includes(player))) {
        return [];
    }

    return remaining;
}

/**
 * Replays the turn buffer on the last committed state, truncating it at the first
 * move the engine rejects (possible after a rebase), and returns the preview plus the
 * moves that survived. Tentative moves never touch the power-plant deck or the seed —
 * any move with hidden side effects commits, ending the buffer — so replaying them on
 * the STRIPPED committed state is exact.
 */
export function replayTurnBuffer(
    committedState: GameState,
    turnMoves: Move[],
    player: number
): { state: GameState; applied: Move[] } {
    let state: GameState = JSON.parse(JSON.stringify(committedState));
    const applied: Move[] = [];

    for (const move of turnMoves) {
        try {
            state = engineMove(state, move, player);
        } catch (err) {
            console.error('dropping turn-buffer tail no longer legal on the committed state', move, err);
            break;
        }
        applied.push(move);
    }

    return { state, applied };
}
