import { availableMoves } from './available-moves';
import type { GameState } from './gamestate';

/** Bid choices are materialized arrays, so sandbox balances must remain bounded. */
export const MAX_ANALYSIS_MONEY = 9999;
export interface SetAnalysisMoney {
    name: 'SetAnalysisMoney';
    data: { player: number; money: number };
}

export function isAnalysisMoneyCommand(input: unknown): input is SetAnalysisMoney {
    return !!input && typeof input === 'object' && (input as SetAnalysisMoney).name === 'SetAnalysisMoney';
}

/** Shared by analysis commands and event replay; never a gameplay move. */
export function applyAnalysisMoney(G: GameState, data: SetAnalysisMoney['data']): void {
    if (!data || !Number.isSafeInteger(data.player) || data.player < 0 || !G.players[data.player])
        throw new Error('Invalid analysis money target seat');
    if (!Number.isSafeInteger(data.money) || data.money < 0 || data.money > MAX_ANALYSIS_MONEY)
        throw new Error(`Analysis money must be an integer between 0 and ${MAX_ANALYSIS_MONEY}`);
    if (G.chosenPowerPlant && data.money < G.players[data.player].bid)
        throw new Error('Analysis money cannot be less than the outstanding bid');
    if (G.players[data.player].money !== data.money && G.analysisKnownMoney) {
        G.analysisKnownMoney = G.analysisKnownMoney.filter((seat) => seat !== data.player);
    }
    G.players[data.player].money = data.money;
    // Reopening a completed powering choice restores its old money. Invalidate
    // private revision checkpoints at this explicit sandbox edit boundary.
    delete G.poweringChoices;
    delete G.revisedPowering;
    delete G.automation;
    if (!G.options.showMoney) G.analysisMoney = 'hypothetical';
    G.players.forEach((seat) => {
        seat.availableMoves = G.currentPlayers.includes(seat.id) ? availableMoves(G, seat) : null;
    });
    G.newTurn = true;
}
