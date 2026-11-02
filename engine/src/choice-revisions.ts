import type { GameState, Player } from './gamestate';
import { Phase } from './gamestate';
import { Move, MoveName } from './move';

export type PoweringChoice = Pick<
    Player,
    | 'money'
    | 'coalLeft'
    | 'oilLeft'
    | 'garbageLeft'
    | 'uraniumLeft'
    | 'powerPlantsNotUsed'
    | 'citiesPowered'
    | 'targetCitiesPowered'
    | 'totalIncome'
> & {
    round: number;
    logStart?: number;
    firstSubmission?: Pick<Move, 'time' | 'serverTime'>[];
    reopened?: boolean;
};
export function rememberPowering(G: GameState, seat: number): void {
    if (G.phase !== Phase.Bureaucracy || G.poweringChoices?.[seat]?.round === G.round) return;
    const p = G.players[seat];
    (G.poweringChoices ??= {})[seat] = {
        round: G.round,
        logStart: G.log.length,
        money: p.money,
        coalLeft: p.coalLeft,
        oilLeft: p.oilLeft,
        garbageLeft: p.garbageLeft,
        uraniumLeft: p.uraniumLeft,
        powerPlantsNotUsed: [...p.powerPlantsNotUsed],
        citiesPowered: p.citiesPowered,
        targetCitiesPowered: p.targetCitiesPowered,
        totalIncome: p.totalIncome,
    };
}
export function canReopenPowering(G: GameState, seat: number): boolean {
    return (
        G.phase === Phase.Bureaucracy &&
        !!G.players[seat]?.passed &&
        !G.players[seat].isDropped &&
        G.currentPlayers.length > 0 &&
        !G.currentPlayers.includes(seat) &&
        G.poweringChoices?.[seat]?.round === G.round
    );
}
export function restorePowering(G: GameState, seat: number): void {
    const p = G.players[seat];
    const snapshot = G.poweringChoices![seat];
    const { round, logStart, firstSubmission, reopened, ...choice } = snapshot;
    if (G.coalStorage !== undefined) G.coalStorage -= choice.coalLeft - p.coalLeft;
    else G.coalSupply -= choice.coalLeft - p.coalLeft;
    G.oilSupply -= choice.oilLeft - p.oilLeft;
    G.garbageSupply -= choice.garbageLeft - p.garbageLeft;
    G.uraniumSupply -= choice.uraniumLeft - p.uraniumLeft;
    Object.assign(p, choice, { powerPlantsNotUsed: [...choice.powerPlantsNotUsed], passed: false });
    (G.revisedPowering ??= {})[seat] = round;
    G.currentPlayers = G.playerOrder.filter((id) => !G.players[id].passed && !G.players[id].isDropped);
}

// Each player's powering is independent until the last Pass resolves upkeep. Drop
// only this player's pending block; other players' choices remain in their order.
// Original submission stamps and clock accounting are bounded metadata, not moves.
export function replacePoweringLog(G: GameState, seat: number): void {
    const choice = G.poweringChoices![seat];
    if (choice.logStart === undefined) throw new Error('Powering history needs replay before revision');
    const removed: number[] = [];
    G.log.forEach((entry, index) => {
        if (index >= choice.logStart! && entry.type === 'move' && entry.player === seat) removed.push(index);
    });
    if (!choice.firstSubmission) {
        choice.firstSubmission = removed.map((index) => {
            const { time, serverTime } = (G.log[index] as import('./log').LogMove).move;
            return { time, serverTime };
        });
    }
    const removedSet = new Set(removed);
    G.log = G.log.filter((_, index) => !removedSet.has(index));
    for (const snapshot of Object.values(G.poweringChoices!)) {
        if (snapshot.round === G.round && snapshot.logStart !== undefined)
            snapshot.logStart -= removed.filter((index) => index < snapshot.logStart!).length;
    }
    choice.reopened = true;
}

export function finishPoweringLog(G: GameState, seat: number, round: number, move: Move): void {
    const choice = G.poweringChoices?.[seat];
    if (choice?.round !== round || !choice.reopened || move.name !== MoveName.Pass) return;
    const entries = G.log.slice(choice.logStart).filter((entry) => entry.type === 'move' && entry.player === seat);
    const stamps = choice.firstSubmission!;
    entries.forEach((entry, index) => {
        if (entry.type !== 'move') return;
        // Preserve the first completion time even when the revised choice powers a
        // different number of plants. The Pass also retains the actual clock event.
        const stamp = entry.move.name === MoveName.Pass ? stamps[stamps.length - 1] : stamps[index] ?? stamps[0];
        if (entry.move.name === MoveName.Pass)
            entry.move.poweringClock = {
                at: move.poweringClock?.at ?? move.serverTime ?? move.time,
                totalTimeUsed: G.players[seat].totalTimeUsed,
                clockStartedAt: G.players[seat].clockStartedAt,
            };
        entry.move.time = stamp?.time;
        entry.move.serverTime = stamp?.serverTime;
    });
    choice.reopened = false;
}
export function bidRevision(G: GameState, seat: number): string | undefined {
    const p = G.players[seat];
    if (
        !p ||
        p.isDropped ||
        p.skipAuction ||
        !G.options.fastBid ||
        G.phase !== Phase.Auction ||
        !G.chosenPowerPlant ||
        !G.currentPlayers.length ||
        G.currentPlayers.includes(seat)
    )
        return undefined;
    return `${G.round}:${G.log.length}:${G.chosenPowerPlant.number}`;
}
export function canReviseChoice(G: GameState, payload: unknown, seat: number): boolean {
    const moves = Array.isArray(payload) ? payload : [payload];
    if (moves.length !== 1 || !moves[0]) return false;
    const m = moves[0] as Move;
    if (m.name === MoveName.ReopenPowering) return canReopenPowering(G, seat) && m.data === G.round;
    const key = bidRevision(G, seat);
    return (
        !!key &&
        m.revision === key &&
        (m.name === MoveName.Bid || (m.name === MoveName.Pass && seat !== G.auctioningPlayer))
    );
}
export function alreadyCreditedPowering(G: GameState, seat: number, phase: Phase, round: number): boolean {
    return phase === Phase.Bureaucracy && G.revisedPowering?.[seat] === round;
}
