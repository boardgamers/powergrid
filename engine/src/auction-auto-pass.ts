import { minimumPlantBid } from './auction-pricing';
import { availableMoves } from './available-moves';
import { move } from './engine';
import { GameState, Phase } from './gamestate';
import { MoveName } from './move';
import { automation } from './premoves';

/** Authoritative live play only. Replays apply the resulting ordinary, logged Pass moves. */
export function autoPassAuctions(G: GameState, serverTime: number): GameState {
    // Each seat can leave the current bidding, then skip its remaining nomination.
    // No plant is bought by this loop without an already submitted winning bid.
    for (let guard = 0; guard < G.players.length * 2 + 1 && G.phase === Phase.Auction; guard++) {
        const minimum = G.chosenPowerPlant
            ? G.options.fastBid
                ? G.minimunBid
                : G.currentBid != null
                ? G.currentBid + 1
                : G.minimunBid
            : Math.min(...G.actualMarket.map((plant) => minimumPlantBid(G, plant)));
        const seat = G.currentPlayers.find((id) => {
            const player = G.players[id];
            if (!G.options.showMoney && player.settings?.autoPassBids !== true) return false;
            // Hidden/stripped states must never be used for an affordability decision.
            if (player.isDropped || player.money < 0 || player.money >= minimum) return false;
            const legal = availableMoves(G, player);
            return (
                !!legal.Pass?.length &&
                Object.entries(legal).every(([name, values]) => name === MoveName.Pass || !values?.length)
            );
        });
        if (seat === undefined) return G;
        G.players[seat].availableMoves = availableMoves(G, G.players[seat]);
        G = move(G, { name: MoveName.Pass, data: true, serverTime }, seat);
        automation(G).increments[seat]++;
        automation(G).liveUpdate = false;
    }
    return G;
}
