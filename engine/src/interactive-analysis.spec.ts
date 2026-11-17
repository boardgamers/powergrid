import { expect } from 'chai';
import 'mocha';
import * as wrapper from '../wrapper';
import { availableMoves } from './available-moves';
import { setup, stripSecret } from './engine';
import { GameState, Phase } from './gamestate';
import { MoveName } from './move';

const clone = (s: GameState): GameState => JSON.parse(JSON.stringify(s));
describe('manual interactive analysis policy', () => {
    it('retains only the creator cash and reopens sealed commitments for every seat', async () => {
        const live = setup(3, { fastBid: true }, 'private');
        const actor = live.currentPlayers[0];
        let source = await wrapper.analysisMove(
            live,
            { name: MoveName.ChoosePowerPlant, data: live.actualMarket[0].number },
            actor
        );
        source = await wrapper.analysisMove(source, { name: MoveName.Bid, data: 20 }, source.currentPlayers[0]);
        const before = clone(source);
        const other = clone(source);
        other.seed = 'another-private-seed';
        other.powerPlantsDeck.reverse();
        other.powerPlantDeckAfterStep3 = [];
        other.hiddenLog = [];
        other.players.forEach((p, i) => {
            if (i !== actor) p.money += 123;
            p.bid += 37;
        });
        const branch = wrapper.createAnalysisScenario(source, { player: actor, seed: 'sandbox' });
        expect(branch).to.deep.equal(wrapper.createAnalysisScenario(other, { player: actor, seed: 'sandbox' }));
        const balances = source.players.map((p, i) => (i === actor ? p.money : 999));
        expect(branch.players.map((p) => p.money)).to.deep.equal(balances);
        expect(branch.players.map((p) => p.bid)).to.deep.equal([0, 0, 0]);
        expect(branch.currentPlayers).to.have.length(3);
        expect(branch.analysisMoney).to.equal('hypothetical');
        expect(branch.analysisKnownMoney).to.deep.equal([actor]);
        expect(wrapper.createAnalysisScenario(branch, { seed: 'resample' }).analysisKnownMoney).to.deep.equal([actor]);
        const edited = await wrapper.analysisMove(
            branch,
            { name: 'SetAnalysisMoney', data: { player: actor, money: 123 } },
            branch.currentPlayers[0]
        );
        expect(edited.analysisKnownMoney).to.deep.equal([]);
        expect(branch.analysisKnownMoney).to.deep.equal([actor]);
        expect(stripSecret(branch).players.map((p) => p.money)).to.deep.equal(balances);
        expect(stripSecret(source).players.map((p) => p.money)).to.deep.equal([-1, -1, -1]);
        expect(clone(source)).to.deep.equal(before);
    });

    for (const player of [0, 1, 2]) {
        it(`preserves seat ${player}'s own zero balance and affordability on regeneration`, () => {
            const source = setup(3, {}, 'source');
            source.players[player].money = 0;
            const branch = wrapper.createAnalysisScenario(source, { player, seed: 'sandbox' });
            const balances = source.players.map((p, i) => (i === player ? 0 : 999));
            expect(branch.players.map((p) => p.money)).to.deep.equal(balances);
            expect(availableMoves(branch, branch.players[player]).ChoosePowerPlant || []).to.have.length(0);
            branch.players[player].money = 10;
            const regenerated = wrapper.createAnalysisScenario(branch, { player, seed: 'new-scenario' });
            expect(regenerated.players.map((p) => p.money)).to.deep.equal(branch.players.map((p) => p.money));
        });
    }

    for (const player of [undefined, -1, 3]) {
        it(`uses hypothetical cash without a valid source seat (${player})`, () => {
            const branch = wrapper.createAnalysisScenario(setup(3, {}, 'source'), { player, seed: 'sandbox' });
            expect(branch.players.map((p) => p.money)).to.deep.equal([999, 999, 999]);
        });
    }

    it('does not treat an already redacted own balance as known cash', () => {
        const source = stripSecret(setup(3, {}, 'source'));
        const branch = wrapper.createAnalysisScenario(source, { player: 0, seed: 'sandbox' });
        expect(branch.players.map((p) => p.money)).to.deep.equal([999, 999, 999]);
    });

    it('hands off opponents manually and spends finite cash without resetting on move or resample', async () => {
        let branch = wrapper.createAnalysisScenario(setup(3, { fastBid: true }, 'source'), { seed: 'sandbox' });
        const actor = branch.currentPlayers[0];
        branch = await wrapper.analysisMove(
            branch,
            { name: MoveName.ChoosePowerPlant, data: branch.actualMarket[0].number },
            actor
        );
        const bidder = branch.currentPlayers[0];
        branch = await wrapper.analysisMove(branch, { name: MoveName.Bid, data: 999 }, bidder);
        expect(branch.currentPlayers).to.have.length(2);
        expect(branch.players.filter((p) => p.bid > 0)).to.have.length(1);
        const second = branch.currentPlayers[0];
        branch = await wrapper.analysisMove(branch, { name: MoveName.Bid, data: 998 }, second);
        expect(branch.currentPlayers).to.have.length(1);
        branch = await wrapper.analysisMove(branch, { name: MoveName.Pass, data: true }, branch.currentPlayers[0]);
        expect(branch.players[bidder].money).to.be.lessThan(999);
        expect(branch.players[bidder].money).to.be.at.least(0);
        expect(wrapper.createAnalysisScenario(branch, { seed: 'resample' }).players.map((p) => p.money)).to.deep.equal(
            branch.players.map((p) => p.money)
        );
        // Finite hypothetical cash still uses the ordinary affordability rules.
        branch.phase = Phase.Auction;
        branch.chosenPowerPlant = undefined;
        branch.round = 2;
        branch.currentPlayers = [bidder];
        branch.players[bidder].skipAuction = false;
        branch.players[bidder].passed = false;
        const legal = availableMoves(branch, branch.players[bidder]);
        expect(legal.ChoosePowerPlant || []).to.have.length(0);
    });

    it('credits ordinary income to the evolving hypothetical balance', async () => {
        let branch = wrapper.createAnalysisScenario(setup(3, {}, 'source'), { seed: 'sandbox' });
        branch.phase = Phase.Bureaucracy;
        branch.currentPlayers = [...branch.playerOrder];
        branch.players.forEach((p) => {
            p.passed = false;
            p.availableMoves = availableMoves(branch, p);
        });
        const actor = branch.currentPlayers[0];
        branch = await wrapper.analysisMove(branch, { name: MoveName.Pass, data: true }, actor);
        expect(branch.players[actor].money).to.equal(1009);
        expect(branch.currentPlayers).to.have.length(2);
        expect(branch.players[branch.currentPlayers[0]].money).to.equal(999);
    });

    it('preserves public cash rather than replacing it with hypothetical cash', () => {
        const source = setup(3, { showMoney: true }, 'source');
        source.players[0].money = 123;
        const branch = wrapper.createAnalysisScenario(source, { seed: 'sandbox' });
        expect(branch.players.map((p) => p.money)).to.deep.equal(source.players.map((p) => p.money));
        expect(branch.analysisMoney).to.equal(undefined);
    });

    for (const showMoney of [false, true])
        it(`does not auto-pass unaffordable opponents (public=${showMoney})`, async () => {
            const branch = setup(3, { showMoney }, 'manual');
            branch.round = 2;
            const actor = branch.currentPlayers[0];
            branch.players.forEach((p) => {
                p.settings = { autoPassBids: true };
                if (p.id !== actor) p.money = 0;
            });
            let result = await wrapper.analysisMove(
                branch,
                { name: MoveName.ChoosePowerPlant, data: branch.actualMarket[0].number },
                actor
            );
            result = await wrapper.analysisMove(result, { name: MoveName.Bid, data: result.minimunBid }, actor);
            expect(result.currentPlayers).to.have.length(1);
            expect(result.currentPlayers[0]).not.to.equal(actor);
            expect(result.players[result.currentPlayers[0]].money).to.equal(0);
            expect(result.players[result.currentPlayers[0]].availableMoves!.Pass).not.to.be.empty;
            expect(result.automation).to.equal(undefined);
        });
});
