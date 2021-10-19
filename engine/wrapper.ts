import { cloneDeep } from 'lodash';
import type { GameState } from './index';
import * as engine from './src/engine';
import type { LogMove } from './src/log';
import { Move, MoveName } from './src/move';
import { asserts } from './src/utils';

export async function init(nbPlayers: number, expansions: string[], options: {}, seed?: string): Promise<GameState> {
    return engine.setup(nbPlayers, options, seed);
}

export function setPlayerMetaData(G: GameState, player: number, metaData: { name: string }) {
    G.players[player].name = metaData.name;

    return G;
}

export async function move(G: GameState, move: Move, player: number) {
    G = engine.move(G, move, player);

    return G;
}

export { ended, scores, stripSecret } from './src/engine';

export function rankings(G: GameState) {
    const sortedPlayers = cloneDeep(G.players)
        .sort((p1, p2) => {
            if (p1.citiesPowered == p2.citiesPowered) {
                return p1.money - p2.money;
            } else {
                return p1.citiesPowered - p2.citiesPowered;
            }
        })
        .map((pl) => pl.id)
        .reverse();

    return G.players.map((pl) => sortedPlayers.indexOf(pl.id) + 1);
}

export function replay(G: GameState) {
    const oldPlayers = G.players;

    const oldG = G;

    G = engine.setup(G.players.length, G.options, G.seed);

    for (let i = 0; i < oldPlayers.length && i < G.players.length; i++) {
        G.players[i].name = oldPlayers[i].name;
    }

    for (const move of oldG.log.filter((event) => event.type === 'move')) {
        asserts<LogMove>(move);

        G = engine.move(G, move.move, move.player);
    }

    return G;
}

export function round(G: GameState) {
    return G.round;
}

export async function dropPlayer(G: GameState, player: number) {
    G.players[player].isDropped = true;

    G = engine.move(G, { name: MoveName.Pass, data: true }, player);

    return G;
}

export function currentPlayer(G: GameState) {
    return G.currentPlayers;
}

export function messages(G: GameState) {
    return {
        messages: [],
        data: G,
    };
}

export function logLength(G: GameState, _player?: number) {
    return G.log.length;
}

export function logSlice(G: GameState, options?: { player?: number; start?: number; end?: number }) {
    const stripped = engine.stripSecret(G, options?.player);
    return {
        log: stripped.log.slice(options?.start, options?.end),
        availableMoves:
            options?.end === undefined
                ? stripped.players.map((pl) => pl.availableMoves)
                : engine
                      .stripSecret(replay({ ...G, log: G.log.slice(0, options!.end) }), options!.player)
                      .players.map((pl) => pl.availableMoves),
    };
}
