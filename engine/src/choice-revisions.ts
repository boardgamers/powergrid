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
> & { round: number };
export function rememberPowering(G: GameState, seat: number): void {
    if (G.phase !== Phase.Bureaucracy || G.poweringChoices?.[seat]?.round === G.round) return;
    const p = G.players[seat];
    (G.poweringChoices ??= {})[seat] = {
        round: G.round,
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
    const { round, ...choice } = G.poweringChoices![seat];
    if (G.coalStorage !== undefined) G.coalStorage -= choice.coalLeft - p.coalLeft;
    else G.coalSupply -= choice.coalLeft - p.coalLeft;
    G.oilSupply -= choice.oilLeft - p.oilLeft;
    G.garbageSupply -= choice.garbageLeft - p.garbageLeft;
    G.uraniumSupply -= choice.uraniumLeft - p.uraniumLeft;
    Object.assign(p, choice, { powerPlantsNotUsed: [...choice.powerPlantsNotUsed], passed: false });
    (G.revisedPowering ??= {})[seat] = round;
    G.currentPlayers = G.playerOrder.filter((id) => !G.players[id].passed && !G.players[id].isDropped);
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
