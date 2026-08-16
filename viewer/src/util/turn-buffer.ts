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
 *   (usually emptying the buffer; a racing extra move may survive).
 * - Someone else's commit (simultaneous Bureaucracy): the new log contains no moves of
 *   ours — keep the whole buffer, to be replayed on the new base.
 * - Anything else (our turn superseded, e.g. auto-played after a drop, or a log that
 *   did not grow monotonically): scrap the buffer.
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

    return turnMoves.slice(appendedOurs.length);
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
