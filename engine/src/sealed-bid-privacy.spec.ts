import { expect } from 'chai';
import 'mocha';
import * as wrapper from '../wrapper';
import { bidRevision } from './choice-revisions';
import { setup, stripSecret } from './engine';
import { GameState } from './gamestate';
import { MoveName } from './move';

const json = (value: unknown) => JSON.parse(JSON.stringify(value));

describe('sealed auction lastMove privacy', () => {
    async function opening(fastBid = true) {
        let state = setup(3, { fastBid, showMoney: false }, 'sealed-privacy');
        const bidder = state.currentPlayers[0];
        const plant = state.players[bidder].availableMoves!.ChoosePowerPlant![0];
        state = await wrapper.move(
            state,
            [
                { name: MoveName.ChoosePowerPlant, data: plant },
                { name: MoveName.Bid, data: plant + 3 },
            ],
            bidder
        );
        return { state, bidder, plant };
    }

    function assertPrivate(state: GameState) {
        const before = json(state);
        for (const viewer of [undefined, -1, 0, 1, 2]) {
            const stripped = json(stripSecret(state, viewer));
            expect(stripped.hiddenLog).to.deep.equal([]);
            expect(stripped.log.filter((e) => e.type === 'move' && e.move.name === MoveName.Bid)).to.deep.equal([]);
            state.players.forEach((player, index) => {
                if (index === viewer) {
                    expect(stripped.players[index].lastMove).to.deep.equal(json(player.lastMove));
                    expect(stripped.players[index].bid).to.equal(player.bid);
                } else {
                    expect(stripped.players[index].lastMove).to.equal(null);
                    expect(stripped.players[index].bid).to.equal(0);
                }
            });
            if (viewer !== undefined && viewer >= 0) {
                expect(json(wrapper.logSlice(state, { player: viewer })).state).to.deep.equal(stripped);
            }
        }
        expect(json(state), 'redaction must not mutate authoritative state').to.deep.equal(before);
    }

    it('hides pending bids and passes from opponents and spectators, including revisions', async () => {
        let { state, bidder, plant } = await opening();
        assertPrivate(state);
        const second = state.currentPlayers[0];
        state = await wrapper.move(state, { name: MoveName.Pass, data: true }, second);
        expect(state.players[second].lastMove!.name).to.equal(MoveName.Pass);
        assertPrivate(state);
        state = await wrapper.move(
            state,
            {
                name: MoveName.Bid,
                data: plant + 5,
                revision: bidRevision(state, second)!,
            },
            second
        );
        assertPrivate(state);
        state = await wrapper.move(
            state,
            {
                name: MoveName.Bid,
                data: plant + 7,
                revision: bidRevision(state, bidder)!,
            },
            bidder
        );
        assertPrivate(state);
        state = await wrapper.move(
            state,
            {
                name: MoveName.Pass,
                data: true,
                revision: bidRevision(state, second)!,
            },
            second
        );
        assertPrivate(state);

        state = await wrapper.move(state, { name: MoveName.Pass, data: true }, state.currentPlayers[0]);
        const publicState = stripSecret(state);
        expect(publicState.hiddenLog).to.deep.equal([]);
        expect(publicState.log.some((e) => e.type === 'move' && e.move.name === MoveName.Bid)).to.equal(true);
        expect(publicState.players.map((p) => p.lastMove)).to.deep.equal(state.players.map((p) => p.lastMove));
    });

    it('preserves public last moves in ordinary open auctions', async () => {
        const { state, bidder } = await opening(false);
        expect(stripSecret(state).players[bidder].lastMove).to.deep.equal(state.players[bidder].lastMove);
    });
});
