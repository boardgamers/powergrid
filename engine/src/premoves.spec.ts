import { expect } from 'chai';
import * as wrapper from '../wrapper';
import { availableMoves } from './available-moves';
import { setup, stripSecret } from './engine';
import { GameState, Phase } from './gamestate';
import { Move, MoveName } from './move';
import { copyState, planMove, replayRoundPlan, startRoundPlan } from './planning';
import { powerPlants } from './powerPlants';
import { automation, PhasePlan, PremoveCommand, runPremoves } from './premoves';
const getPowerPlant = (number: number) => copyState(powerPlants.find((p) => p.number === number)!);

const pass: Move = { name: MoveName.Pass, data: true };
export function position(): GameState {
    const G = setup(3, { map: 'Germany', variant: 'original' }, 'premoves');
    G.round = 3;
    G.phase = Phase.Resources;
    G.playerOrder = [2, 1, 0];
    G.currentPlayers = [1];
    G.players.forEach((p, i) => {
        p.name = ['You', 'Ada', 'Leo'][i];
        p.money = 70;
        p.powerPlants = [getPowerPlant(4), getPowerPlant(13)];
        p.coalCapacity = 4;
        p.coalLeft = 2;
        p.powerPlantsNotUsed = [4, 13];
        p.passed = i === 0;
        p.skipAuction = true;
        p.availableMoves = null;
    });
    G.players[1].availableMoves = availableMoves(G, G.players[1]);
    G.newTurn = true;
    return G;
}
function fullPlan(G = position()): PhasePlan[] {
    let plan = startRoundPlan(G, 0);
    for (let i = 0; i < 2; i++) {
        const city = plan.state.players[0].availableMoves!.Build!.slice().sort((a, b) => a.price - b.price)[0];
        plan = planMove(plan, { name: MoveName.Build, data: city });
    }
    plan = planMove(plan, pass);
    for (const number of [4, 13]) {
        const use = plan.state.players[0].availableMoves!.UsePowerPlant!.find((m) => m.powerPlant === number)!;
        plan = planMove(plan, { name: MoveName.UsePowerPlant, data: use });
    }
    plan = planMove(plan, pass);
    return [Phase.Building, Phase.Bureaucracy].map((phase) => ({
        phase: phase as Phase.Building | Phase.Bureaucracy,
        moves: plan.entries.filter((e) => e.phase === phase).map((e) => e.move),
    }));
}
const request = (phases: PhasePlan[], revision = 0, requestId = 'test'): PremoveCommand => ({
    type: 'premoves',
    round: 3,
    revision,
    requestId,
    phases,
});

describe('current-round planning and premoves', () => {
    it('simulates affordable cities, fuel use and income without altering the live board or starting a new round', () => {
        const G = position(),
            saved = JSON.stringify(G);
        const entries = fullPlan(G).reduce(
            (all, p) => all.concat(p.moves.map((move) => ({ phase: p.phase, move }))),
            [] as { phase: Phase; move: Move }[]
        );
        const plan = replayRoundPlan(stripSecret(G, 0), 0, entries);
        expect(plan.finished).to.equal(true);
        expect(plan.state.round).to.equal(3);
        expect(plan.income).to.equal(33);
        expect(plan.state.players[0].coalLeft).to.equal(0);
        expect(JSON.stringify(G)).to.equal(saved);
        expect(() => planMove(plan, pass)).to.throw('ends after powering');
    });
    it('keeps the known market stable while simulating city builds that would retire a plant', () => {
        const G = position();
        G.players[0].money = 300;
        let plan = startRoundPlan(stripSecret(G, 0), 0);
        for (let i = 0; i < 4; i++) {
            const city = plan.state.players[0].availableMoves!.Build!.slice().sort((a, b) => a.price - b.price)[0];
            plan = planMove(plan, { name: MoveName.Build, data: city });
        }
        expect(plan.state.players[0].cities).to.have.length(4);
        expect(plan.state.actualMarket).to.deep.equal(G.actualMarket);
        expect(plan.state.futureMarket).to.deep.equal(G.futureMarket);
        expect(plan.state.cardsLeft).to.equal(G.cardsLeft);
        expect(plan.state.step).to.equal(G.step);
        expect(plan.state.players[0].powerPlants).to.deep.equal(G.players[0].powerPlants);
    });
    it('ends at final scoring without awarding normal income or consuming fuel', () => {
        const G = position();
        G.citiesToEndGame = 2;
        let plan = startRoundPlan(stripSecret(G, 0), 0);
        for (let i = 0; i < 2; i++) {
            const city = plan.state.players[0].availableMoves!.Build!.slice().sort((a, b) => a.price - b.price)[0];
            plan = planMove(plan, { name: MoveName.Build, data: city });
        }
        const money = plan.state.players[0].money;
        plan = planMove(plan, pass);
        expect(plan.finalScoring).to.equal(true);
        expect(plan.finished).to.equal(true);
        expect(plan.income).to.equal(0);
        expect(plan.state.players[0].money).to.equal(money);
        expect(plan.state.players[0].citiesPowered).to.equal(2);
        expect(plan.state.players[0].coalLeft).to.equal(2);
        expect(plan.entries.some((e) => e.phase === Phase.Bureaucracy)).to.equal(false);
    });
    it('simulates a chosen winning price, or no purchase, then continues through resources', () => {
        const G = position();
        G.phase = Phase.Auction;
        G.players[0].skipAuction = false;
        G.players[0].passed = false;
        const plan = startRoundPlan(stripSecret(G, 0), 0);
        const number = plan.state.players[0].availableMoves!.ChoosePowerPlant!.find((n) => n !== 4 && n !== 13)!;
        const selected = planMove(plan, { name: MoveName.ChoosePowerPlant, data: number });
        expect(selected.state.players[0].money).to.equal(70);
        const bought = planMove(selected, { name: MoveName.Bid, data: 25 });
        expect(bought.state.phase).to.equal(Phase.Resources);
        expect(bought.state.players[0].money).to.equal(45);
        expect(bought.state.players[0].powerPlants.some((p) => p.number === number)).to.equal(true);
        const skipped = planMove(plan, pass);
        expect(skipped.state.phase).to.equal(Phase.Resources);
        expect(skipped.state.players[0].money).to.equal(70);
        expect(() => planMove(selected, { name: MoveName.Bid, data: 71 })).to.throw('affordable');
        const opening = setup(3, { map: 'Germany', variant: 'original' }, 'skip-plant');
        expect(availableMoves(opening, opening.players[0]).Pass).to.equal(undefined);
        const openingPlan = startRoundPlan(opening, 0);
        expect(openingPlan.state.players[0].availableMoves!.Pass).to.deep.equal([true]);
        expect(planMove(openingPlan, pass).state.phase).to.equal(Phase.Resources);
    });
    it('queues privately off turn, executes each phase, and credits increments only when executed', async () => {
        const G = position(),
            phases = fullPlan(G),
            start = G.players[0].money;
        expect(wrapper.canMoveOutOfTurn(G, request(phases), 0)).to.equal(true);
        let saved = await wrapper.move(copyState(G), request(phases), 0);
        expect(saved.players[0].cities).to.have.length(0);
        expect(wrapper.isLiveUpdate(saved)).to.equal(true);
        expect(wrapper.timeIncrements(saved)).to.deep.equal([0, 0, 0]);
        expect(Object.keys(stripSecret(saved, 1).automation!.plans)).to.deep.equal([]);
        expect(Object.keys(stripSecret(saved).automation!.plans)).to.deep.equal([]);
        saved = await wrapper.move(saved, pass, 1);
        saved = await wrapper.move(saved, pass, 2);
        expect(saved.players[0].cities).to.have.length(2);
        expect(wrapper.timeIncrements(saved)[0]).to.equal(1);
        expect(saved.automation!.plans[0].phases.map((p) => p.phase)).to.deep.equal([Phase.Bureaucracy]);
        saved = await wrapper.move(saved, pass, 1);
        saved = await wrapper.move(saved, pass, 2);
        expect(saved.players[0].coalLeft).to.equal(0);
        expect(saved.automation!.plans[0].phases).to.have.length(0);
        expect(wrapper.timeIncrements(saved)[0]).to.equal(2);
        const cost = phases[0].moves
            .filter((m) => m.name === MoveName.Build)
            .reduce((sum, m) => sum + (m.data as any).price, 0);
        expect(saved.players[0].money).to.equal(start - cost + 33);
    });
    it('cancels the queue and rejects stale edits or duplicate execution', async () => {
        let G = await wrapper.move(position(), request(fullPlan()), 0);
        G = await wrapper.move(G, request(fullPlan(), 0), 0);
        expect(G.automation!.plans[0].revision).to.equal(1);
        G = await wrapper.move(G, request([], 1, 'cancel-all'), 0);
        expect(G.automation!.plans[0].phases).to.have.length(0);
        try {
            await wrapper.move(copyState(G), request([], 1, 'stale'), 0);
            throw Error('accepted');
        } catch (e) {
            expect(e.message).to.contain('queue changed');
        }
        expect(G.automation!.plans[0].phases).to.have.length(0);
        expect(wrapper.timeIncrements(G)[0]).to.equal(0);
    });
    it('rejects auctions, resources, incomplete phases and plans made before buying is finished', async () => {
        for (const phases of [
            [{ phase: Phase.Auction, moves: [pass] }],
            [{ phase: Phase.Resources, moves: [pass] }],
            [{ phase: Phase.Building, moves: fullPlan()[0].moves.slice(0, -1) }],
        ]) {
            let failed = false;
            try {
                await wrapper.move(position(), request(phases as PhasePlan[]), 0);
            } catch {
                failed = true;
            }
            expect(failed).to.equal(true);
        }
        const G = position();
        G.players[0].passed = false;
        let failed = false;
        try {
            await wrapper.move(G, request(fullPlan()), 0);
        } catch {
            failed = true;
        }
        expect(failed).to.equal(true);
    });
    it('stops a changed city plan atomically, without spending on its earlier cities', async () => {
        const phases = fullPlan();
        let G = await wrapper.move(position(), request(phases), 0);
        const second = (phases[0].moves[1].data as any).name;
        G.players[1].cities.push({ name: second, position: 0 });
        G.phase = Phase.Building;
        G.currentPlayers = [0];
        G.players[0].passed = false;
        G = runPremoves(G);
        expect(G.players[0].cities).to.have.length(0);
        expect(G.players[0].money).to.equal(70);
        expect(G.automation!.plans[0].phases).to.have.length(0);
        expect(G.automation!.plans[0].notice).to.contain('Premoves stopped');
        expect(wrapper.timeIncrements(G)[0]).to.equal(0);
    });
    it('stops when an extra house slot changes the planned price', async () => {
        let G = position();
        G.step = 2;
        const phases = fullPlan(G);
        G = await wrapper.move(G, request(phases), 0);
        G.players[1].cities.push({ name: (phases[0].moves[0].data as any).name, position: 0 });
        G.phase = Phase.Building;
        G.currentPlayers = [0];
        G.players[0].passed = false;
        G = runPremoves(G);
        expect(G.players[0].money).to.equal(70);
        expect(G.automation!.plans[0].notice).to.contain('instead of the planned');
    });
    it('does not use unavailable fuel or let a plan carry into the next round', async () => {
        let G = await wrapper.move(position(), request(fullPlan()), 0);
        G.players[0].coalLeft = 0;
        G.phase = Phase.Bureaucracy;
        G.currentPlayers = [0];
        G.automation!.plans[0].phases.shift();
        G = runPremoves(G);
        expect(G.players[0].money).to.equal(70);
        expect(G.automation!.plans[0].notice).to.contain('fuel');
        G = await wrapper.move(position(), request(fullPlan()), 0);
        G.round++;
        G = runPremoves(G);
        expect(G.automation!.plans[0].phases).to.have.length(0);
        expect(G.players[0].cities).to.have.length(0);
    });
    it('manual building preserves queued powering, and tentative clicks award no increments', async () => {
        let G = position();
        G.phase = Phase.Building;
        G.currentPlayers = [0];
        G.players[0].passed = false;
        G.players[0].availableMoves = availableMoves(G, G.players[0]);
        const phases = fullPlan(G);
        // Saved queues can race a manual phase from another browser.
        automation(G).plans[0] = { round: 3, revision: 1, requestId: 'saved', phases };
        const tentative = await wrapper.move(copyState(G), phases[0].moves[0], 0);
        expect(wrapper.toSave(tentative)).to.equal(undefined);
        expect(wrapper.timeIncrements(tentative)[0]).to.equal(0);
        G = await wrapper.move(G, phases[0].moves, 0);
        expect(G.automation!.plans[0].phases.map((p) => p.phase)).to.deep.equal([Phase.Bureaucracy]);
        expect(wrapper.timeIncrements(G)[0]).to.equal(1);
    });
});
