import { availableMoves, AvailableMoves } from './available-moves';
import { move } from './engine';
import { GameState, Phase } from './gamestate';
import { MoveName } from './move';
import { automation } from './premoves';

function onlyPass(legal: AvailableMoves): boolean {
    return (
        !!legal.Pass?.length &&
        Object.entries(legal).every(([name, values]) => name === MoveName.Pass || !values?.length)
    );
}

/** Live server policy, never called by replay or interactive analysis. */
export function autoPassResourcesAndBuilding(G: GameState, serverTime: number): GameState {
    // Never commit an undoable purchase/build on behalf of its owner.
    if (G.newTurn === false || G.achievementAnalysis) return G;
    if (G.phase !== Phase.Resources && G.phase !== Phase.Building) return G;
    const setting = G.phase === Phase.Resources ? 'autoPassResources' : 'autoPassBuilding';
    const seat = G.currentPlayers.find((id) => {
        const player = G.players[id];
        if (player.isDropped || !Number.isFinite(player.money) || player.money < 0) return false;
        if (!onlyPass(availableMoves(G, player))) return false;
        if (G.options.showMoney || player.settings?.[setting] === true) return true;
        // These phases enumerate resources/cities, never one bid per Elektro.
        // Read-only copies keep both money and options untouched. In the public
        // impossibility probe, exclude the historical 9999 "unbuildable" sentinel
        // even in legacy games without stallEnds. Actual legal moves above still
        // take precedence, including legacy builds bought for >=9999.
        const probe = { ...G, options: { ...G.options, stallEnds: true } };
        return onlyPass(availableMoves(probe, { ...player, money: Number.MAX_SAFE_INTEGER }));
    });
    if (seat === undefined) return G;
    G.players[seat].availableMoves = availableMoves(G, G.players[seat]);
    // Ordinary Pass only: neither the private setting nor the reason is logged.
    G = move(G, { name: MoveName.Pass, data: true, serverTime }, seat);
    automation(G).increments[seat]++;
    automation(G).liveUpdate = false;
    // Yield after each turn so a newly current player's queued phase runs first.
    return G;
}
