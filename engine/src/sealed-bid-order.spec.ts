import { expect } from 'chai';
import 'mocha';
import * as wrapper from '../wrapper';
import { bidRevision } from './choice-revisions';
import { move, setup, stripSecret } from './engine';
import { LogMove } from './log';
import { MoveName } from './move';

describe('sealed auction reveal order', () => {
    for (const order of [
        [2, 0, 1],
        [1, 2, 0],
    ]) {
        it(`reveals bids and revised passes in seat order after submissions ${order}`, () => {
            let state = setup(3, { fastBid: true, showMoney: false }, 'sealed-order');
            const auctioneer = state.currentPlayers[0];
            const plant = state.players[auctioneer].availableMoves!.ChoosePowerPlant![0];
            state = move(state, { name: MoveName.ChoosePowerPlant, data: plant }, auctioneer);
            const start = state.log.length;
            const passer = order.find((seat) => seat !== auctioneer)!;
            for (const seat of order) {
                state = move(state, { name: MoveName.Bid, data: plant + 5 }, seat);
                if (seat === passer) {
                    state = move(
                        state,
                        {
                            name: MoveName.Pass,
                            data: true,
                            revision: bidRevision(state, seat)!,
                        },
                        seat
                    );
                }
                if (seat !== order[2]) {
                    expect(state.log).to.have.length(start);
                    expect(stripSecret(state).hiddenLog).to.deep.equal([]);
                    expect(state.hiddenLog.map((entry) => (entry as LogMove).player)).to.deep.equal(
                        order.slice(0, order.indexOf(seat) + 1)
                    );
                }
            }
            const revealed = state.log.slice(start, start + 3) as LogMove[];
            expect(revealed.map((entry) => entry.player)).to.deep.equal([0, 1, 2]);
            expect(revealed.map((entry) => entry.move.name)).to.deep.equal(
                [0, 1, 2].map((seat) => (seat === passer ? MoveName.Pass : MoveName.Bid))
            );
            expect(state.hiddenLog).to.deep.equal([]);
            // Equal bids still use the auctioneer-first tie break, not reveal order.
            expect(state.players[auctioneer].powerPlants.map((p) => p.number)).to.include(plant);
            expect(state.players[auctioneer].money).to.equal(50 - plant - 5);
            const replayed = wrapper.replay(state);
            expect(replayed.log).to.deep.equal(state.log);
            expect(replayed.players.map((p) => [p.money, p.powerPlants])).to.deep.equal(
                state.players.map((p) => [p.money, p.powerPlants])
            );
        });
    }
});
