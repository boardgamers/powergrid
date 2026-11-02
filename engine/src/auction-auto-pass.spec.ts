import { expect } from 'chai';
import { cloneDeep } from 'lodash';
import 'mocha';
import * as wrapper from '../wrapper';
import { autoPassAuctions } from './auction-auto-pass';
import { availableMoves } from './available-moves';
import { setup, stripSecret } from './engine';
import { GameState, Phase } from './gamestate';
import { Move, MoveName } from './move';
import { powerPlants } from './powerPlants';

const json = (value: unknown) => JSON.parse(JSON.stringify(value));
const pass: Move = { name: MoveName.Pass, data: true };
function position(showMoney = true, fastBid = false): GameState {
    const G = setup(3, { map: 'Germany', variant: 'original', showMoney, fastBid }, 'auto-pass');
    G.round = 2;
    G.currentPlayers = [0];
    G.playerOrder = [0, 1, 2];
    G.players.forEach((p, i) => {
        p.money = [50, 10, 40][i];
        p.availableMoves = i === 0 ? availableMoves(G, p) : null;
    });
    return G;
}
const opening = (G: GameState, bid = 10): Move[] => [
    { name: MoveName.ChoosePowerPlant, data: G.actualMarket[0].number },
    { name: MoveName.Bid, data: bid },
];

describe('authoritative auction auto-pass', () => {
    it('skips a public-money player who cannot raise, logs the pass and preserves an affordable next bidder', async () => {
        const G = await wrapper.move(position(), opening(position()), 0);
        expect(G.currentPlayers).to.deep.equal([2]);
        expect(G.players[1].passed).to.equal(true);
        expect(G.players[0].passed).to.equal(false);
        expect(G.log.slice(-1)[0]).to.include({ type: 'move', player: 1 });
        expect(G.players[2].availableMoves!.Bid![0]).to.equal(11);
        expect(wrapper.timeIncrements(G)).to.deep.equal([1, 1, 0]);
        expect(wrapper.toSave(G)).to.equal(G);
        const result = await wrapper.move(G, pass, 2);
        expect(result.players[0].money).to.equal(40);
        expect(result.players[0].powerPlants).to.have.length(1);
    });

    it('leaves hidden money alone unless that player opted in; turning it off restores manual passing', async () => {
        const G = position(false);
        expect(wrapper.playerSettings(G, 1)).to.deep.equal({ autoPassBids: false });
        expect((await wrapper.move(cloneDeep(G), opening(G), 0)).currentPlayers).to.deep.equal([1]);
        wrapper.setPlayerSettings(G, 1, { autoPassBids: true });
        expect((await wrapper.move(cloneDeep(G), opening(G), 0)).currentPlayers).to.deep.equal([2]);
        wrapper.setPlayerSettings(G, 1, { autoPassBids: false });
        expect((await wrapper.move(G, opening(G), 0)).currentPlayers).to.deep.equal([1]);
    });

    it('keeps settings private and strictly boolean', () => {
        const G = position(false);
        wrapper.setPlayerSettings(G, 1, { autoPassBids: true });
        expect(stripSecret(G, 0).players[1].settings).to.equal(undefined);
        expect(stripSecret(G).players[1].settings).to.equal(undefined);
        expect(stripSecret(G, 1).players[1].settings).to.deep.equal({ autoPassBids: true });
        wrapper.setPlayerSettings(G, 1, { autoPassBids: 'true' });
        expect(wrapper.playerSettings(G, 1)).to.deep.equal({ autoPassBids: false });
    });

    it('never advances turns when the host saves settings', () => {
        const G = position(false);
        G.currentPlayers = [1];
        const before = json(G);
        wrapper.setPlayerSettings(G, 1, { autoPassBids: true });
        delete G.players[1].settings;
        expect(json(G)).to.deep.equal(before);
    });

    for (const publicMoney of [true, false]) {
        it(`preserves sealed-bid privacy and permits an exact minimum bid (${
            publicMoney ? 'public' : 'opt-in'
        })`, async () => {
            let G = position(publicMoney, true);
            const minimum = G.actualMarket[0].number;
            G.players[1].money = minimum - 1;
            G.players[2].money = minimum;
            if (!publicMoney) wrapper.setPlayerSettings(G, 1, { autoPassBids: true });
            G = await wrapper.move(G, opening(G, minimum), 0);
            expect(G.currentPlayers).to.deep.equal([2]);
            expect(G.hiddenLog).to.have.length(2);
            expect(G.hiddenLog[1]).to.include({ player: 1 });
            expect(G.log.some((entry) => entry.type === 'move' && entry.player === 1)).to.equal(false);
            expect(stripSecret(G, 2).hiddenLog).to.have.length(0);
            expect(G.players[2].availableMoves!.Bid).to.deep.equal([minimum]);
            G = await wrapper.move(G, { name: MoveName.Bid, data: minimum }, 2);
            expect(G.hiddenLog).to.have.length(0);
            expect(G.players.reduce((n, p) => n + p.powerPlants.length, 0)).to.equal(1);
        });
    }

    it('auto-skips nominations, but retains an affordable Recharged discount', () => {
        const G = position();
        G.players[0].money = 1;
        expect(autoPassAuctions(cloneDeep(G), 123).players[0].skipAuction).to.equal(true);
        G.options.variant = 'recharged';
        G.plantDiscountActive = true;
        const legal = availableMoves(G, G.players[0]);
        expect(legal.ChoosePowerPlant).to.deep.equal([G.actualMarket[0].number]);
        expect(autoPassAuctions(G, 123).currentPlayers).to.deep.equal([0]);
    });

    it('uses the discounted minimum during bidding too', async () => {
        const G = position();
        G.options.variant = 'recharged';
        G.plantDiscountActive = true;
        G.players[1].money = 2;
        const result = await wrapper.move(G, opening(G, 1), 0);
        expect(result.currentPlayers).to.deep.equal([1]);
        expect(result.players[1].availableMoves!.Bid).to.deep.equal([2]);
    });

    it('never bypasses plant discards or first-round mandatory buying', () => {
        const G = position();
        G.players[0].money = 0;
        G.players[0].powerPlants = cloneDeep(powerPlants.slice(0, 4));
        expect(autoPassAuctions(G, 123).players[0].skipAuction).to.equal(false);
        G.players[0].powerPlants = [];
        G.round = 1;
        expect(autoPassAuctions(G, 123).players[0].skipAuction).to.equal(false);
    });

    it('does not infer unaffordability from stripped money', () => {
        const G = position();
        G.players[0].money = -1;
        expect(autoPassAuctions(G, 123).players[0].skipAuction).to.equal(false);
    });

    for (const fastBid of [false, true]) {
        it(`replays logged auto-passes after settings change (${fastBid ? 'sealed' : 'open'})`, async () => {
            let G = setup(3, { map: 'Germany', variant: 'original', fastBid }, 'auto-pass-replay');
            const first = G.currentPlayers[0];
            const plant = G.actualMarket[0].number;
            for (const p of G.players) wrapper.setPlayerSettings(G, p.id, { autoPassBids: true });
            if (fastBid) {
                G = await wrapper.move(G, { name: MoveName.ChoosePowerPlant, data: plant }, first);
                // Normal setup has enough money for everyone; verify the old/manual
                // history remains manual even when all current settings are enabled.
                G = await wrapper.move(G, { name: MoveName.Bid, data: 50 }, first);
                G = await wrapper.move(G, pass, G.currentPlayers[0]);
                expect(json(wrapper.replay(G))).to.deep.equal(json(G));
                G = await wrapper.move(G, pass, G.currentPlayers[0]);
            } else G = await wrapper.move(G, opening(G, 50), first);
            for (const p of G.players) wrapper.setPlayerSettings(G, p.id, { autoPassBids: false });
            expect(G.players[first].powerPlants).to.have.length(1);
            expect(json(wrapper.replay(G))).to.deep.equal(json(G));
        });
    }

    it('finishes an all-unaffordable auction phase without looping', () => {
        const G = position();
        G.players.forEach((p) => (p.money = 0));
        expect(autoPassAuctions(G, 123).phase).to.equal(Phase.Resources);
        expect(wrapper.timeIncrements(G)).to.deep.equal([1, 1, 1]);
    });
});
