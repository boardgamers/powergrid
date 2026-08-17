import type { GameState } from './index';
import * as engine from './src/engine';
import { playersSortedByScore } from './src/engine';
import { GameOptions } from './src/gamestate';
import type { LogMove } from './src/log';
import { Move, MoveName } from './src/move';
import { asserts } from './src/utils';

export async function init(
    nbPlayers: number,
    expansions: string[],
    options: GameOptions,
    seed?: string
): Promise<GameState> {
    return engine.setup(nbPlayers, options, seed);
}

export function setPlayerMetaData(G: GameState, player: number, metaData: { name: string }): GameState {
    G.players[player].name = metaData.name;

    return G;
}

/**
 * Execute the current turn of `player` so far.
 *
 * The payload is the **whole turn buffer**: an array of atomic moves accumulated by the
 * viewer since the last committed state. `G` is always a committed state (tentative
 * states are never persisted by the platform), so the buffer is replayed from it in
 * order. A bare move object is also accepted and treated as a one-element buffer.
 *
 * While the resulting state is still tentative (the mover could undo, i.e.
 * `G.newTurn === false`), `toSave` returns `undefined`: the platform then sends the
 * tentative state back to the acting player without persisting it or granting a time
 * increment. Undo is implemented by the viewer replaying a shortened buffer — or, when
 * the buffer empties, by doing nothing at all, since the saved state *is* the turn
 * start. Each move carries the wall-clock stamp given to it when it FIRST entered the
 * buffer, so successive replays of the same buffer tick the in-game clocks identically.
 */
export async function move(G: GameState, move: Move | Move[] | null | undefined, player: number): Promise<GameState> {
    const moves: Move[] = move == null ? [] : Array.isArray(move) ? move : [move];

    if (moves.length === 0) {
        // Nothing to apply — flag the result as tentative so nothing gets persisted
        // and no time increment is granted.
        return { ...G, newTurn: false };
    }

    for (let i = 0; i < moves.length; i++) {
        G = engine.move(G, moves[i], player);

        // The buffer must describe at most ONE turn: committing is what grants the
        // mover their per-turn time increment. Without this guard a buffer like
        // `[..., Pass, ...more]` — legal in the degenerate case where the same player
        // is up again right away (e.g. the only other players are dropped, or a
        // Building-phase move commits early because a market event followed it) —
        // would replay across the turn boundary and commit several turns for a single
        // increment. Any illegal move in the buffer throws wholesale; the platform
        // discards the state either way.
        if (G.newTurn !== false && i < moves.length - 1) {
            throw new Error('The turn buffer continues past a turn boundary: only one turn may be played per call');
        }
    }

    return G;
}

/**
 * Only committed states are persisted. Tentative states (mid-turn, still undoable)
 * return `undefined` so the platform neither saves them nor grants a time increment.
 */
export function toSave(G: GameState): GameState | undefined {
    return G.newTurn === false ? undefined : G;
}

export { ended, scores, stripSecret } from './src/engine';

/**
 * Play a full turn for `player`. The engine's own `moveAI` plays one atomic move at a
 * time, which can leave the state tentative (`toSave` would refuse to persist it); the
 * platform's bot driver and `dropPlayer` auto-play both require committed states, so we
 * keep playing until the turn commits.
 */
export function moveAI(G: GameState, player: number): GameState {
    for (let i = 0; i < 500 && !engine.ended(G) && G.currentPlayers.includes(player); i++) {
        G = engine.moveAI(G, player);

        if (G.newTurn !== false) {
            return G;
        }
    }

    // Safety net — should be unreachable (every phase offers the AI a committing move:
    // Pass wherever it exists, and the choose/bid/discard prompts all commit by handing
    // control on or pushing a resolution event). The state is consistent (every atomic
    // move was legal and logged), it just did not reach a turn boundary; persisting it
    // keeps the game going instead of wedging it. Shout so a would-be livelock is
    // visible in the server logs instead of being silently masked.
    console.error(
        `moveAI: force-committing after 500 moves without reaching a turn boundary (player ${player}, phase ${G.phase}, round ${G.round})`
    );
    G.newTurn = true;

    return G;
}

export function rankings(G: GameState): number[] {
    const sortedPlayers = playersSortedByScore(G);
    sortedPlayers.forEach((player, index) => {
        player.ranking = index + 1;

        if (index > 0) {
            const prev = sortedPlayers[index - 1];
            if (
                player.citiesPowered === prev.citiesPowered &&
                player.money === prev.money &&
                player.cities.length === prev.cities.length
            ) {
                player.ranking = prev.ranking;
            }
        }
    });

    return G.players.map((pl) => sortedPlayers.find((spl) => pl.id === spl.id)!.ranking!);
}

export function factions(G: GameState): string[] {
    return G.players.map((pl) => pl.color ?? engine.playerColors[pl.id]);
}

export function replay(G: GameState, { to = Infinity }: { to?: number } = {}): GameState {
    const oldPlayers = G.players;

    const oldG = G;

    G = engine.setup(G.players.length, G.options, G.seed);

    for (let i = 0; i < oldPlayers.length && i < G.players.length; i++) {
        G.players[i].name = oldPlayers[i].name;
    }

    // The visible log freezes during a fastBid auction: the simultaneous bids (and
    // bid-phase passes) go to `G.hiddenLog` and are only flushed to `G.log` when the
    // last bid resolves the auction. A state saved mid-auction therefore keeps its
    // newest moves in `hiddenLog`, and whenever `hiddenLog` is non-empty it holds
    // exactly the moves made after the last visible entry, in order — so a full
    // replay must run the visible log followed by the hidden log to reproduce the
    // state faithfully. Truncated replays (`to` inside the visible log) reconstruct
    // a historical state and must NOT append the hidden log.
    const items = to >= oldG.log.length ? [...oldG.log, ...(oldG.hiddenLog ?? [])] : oldG.log.slice(0, to);

    for (const move of items.filter((event) => event.type === 'move')) {
        asserts<LogMove>(move);

        G = engine.move(G, move.move, move.player);
    }

    return G;
}

export function round(G: GameState): number {
    return G.round;
}

// Ceiling on the moves auto-played for one dropped player's turn. Real turns resolve in
// a handful — the longest is a Resources phase bought one cube at a time — so this sits
// orders of magnitude above any legitimate turn and only ever trips on a stuck state.
const MAX_AUTO_MOVES = 1000;

export async function dropPlayer(G: GameState, playerNum: number): Promise<GameState> {
    const player = G.players[playerNum];
    player.isDropped = true;

    G.log.push({
        type: 'event',
        event: `Player ${playerNum} was dropped`,
    });

    if (player.availableMoves?.[MoveName.Pass]) {
        G = engine.move(G, { name: MoveName.Pass, data: true }, playerNum);
    } else {
        let autoMoves = 0;

        while (G.currentPlayers.includes(playerNum)) {
            if (++autoMoves > MAX_AUTO_MOVES) {
                // A state moveAI cannot advance would otherwise spin this loop forever,
                // pinning a game-server worker at 100% CPU with no request ever
                // returning. Fail loudly instead: a thrown error is recoverable and
                // diagnosable, a hung worker is neither.
                throw new Error(
                    `dropPlayer: player ${playerNum} is still current after ${MAX_AUTO_MOVES} auto-played ` +
                        `moves (phase ${G.phase}, round ${G.round}) — aborting to avoid an infinite loop`
                );
            }

            G = engine.moveAI(G, playerNum);
        }
    }

    // Dropping a player must always yield a committed state: `G` was committed to
    // begin with (tentative states are never persisted), and the auto-play above ends
    // either with a Pass or with the dropped player leaving currentPlayers — both
    // commit. Force the flag anyway (it costs nothing) so an unexpected auto-play path
    // can never leave the persisted state un-saveable.
    G.newTurn = true;

    return G;
}

export function currentPlayer(G: GameState): number[] {
    return G.currentPlayers;
}

export function messages(G: GameState) {
    return {
        messages: [],
        data: G,
    };
}

export function logLength(G: GameState, _player?: number): number {
    return G.log.length;
}

export function logSlice(G: GameState, options?: { player?: number; start?: number; end?: number }) {
    const stripped = engine.stripSecret(G, options?.player);

    // `stripSecret` only leaves a player's own `availableMoves` intact for the index it
    // is given; everyone else is blanked to `{}`. The platform's move route is
    // logged-in and always passes the mover's index, but `GET /gameplay/:id/log` is not
    // — it derives the index with `findIndex`, which yields **-1** whenever the user
    // cannot be resolved. Handing back a `state` built that way tells the acting
    // player's viewer they have no moves: the board renders and nothing is clickable
    // until they re-enter the game (which takes the `fetchState` path instead).
    //
    // That blanking predates the tentative-turn model and was harmless while the viewer
    // ignored this payload. Now that the viewer adopts `state` from it, only offer the
    // state when we actually know whose it is; without it `launch.ts` falls back to
    // `fetchState`, which is exactly the old behaviour.
    const playerKnown = options?.player != undefined && options.player >= 0;

    return {
        // The full (stripped) state. This is how the acting player's viewer receives
        // tentative states: they are never persisted or broadcast, only returned in the
        // move response's log slice.
        state: playerKnown ? stripped : undefined,
        log: stripped.log.slice(options?.start, options?.end),
        availableMoves:
            options?.end === undefined
                ? stripped.players.map((pl) => pl.availableMoves)
                : engine
                      .stripSecret(replay(G, { to: options.end }), options!.player)
                      .players.map((pl) => pl.availableMoves),
    };
}
