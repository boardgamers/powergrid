import { expect } from 'chai';
import { cloneDeep } from 'lodash';
import 'mocha';
import * as wrapper from '../wrapper';
import { MAX_ANALYSIS_MONEY, SetAnalysisMoney } from './analysis-money';
import { availableMoves } from './available-moves';
import { rememberPowering } from './choice-revisions';
import * as engine from './engine';
import { Phase } from './gamestate';
import { Move, MoveName } from './move';

const command = (player: number, money: number): SetAnalysisMoney => ({
    name: 'SetAnalysisMoney',
    data: { player, money },
});
const setup = () => engine.setup(3, { fastBid: true }, 'analysis-money');
async function rejects(run: () => Promise<unknown>) {
    let error: unknown;
    try {
        await run();
    } catch (e) {
        error = e;
    }
    expect(error).to.be.instanceOf(Error);
}

describe('analysis money commands', () => {
    for (const target of [0, 1, 2])
        it(`edits seat ${target} without mutating the source, and survives resampling`, async () => {
            const source = wrapper.createAnalysisScenario(setup(), { seed: 'branch' });
            const before = cloneDeep(source);
            const result = await wrapper.analysisMove(source, command(target, 0), source.currentPlayers[0]);
            expect(source).to.deep.equal(before);
            expect(result.players[target].money).to.equal(0);
            expect(result.phase).to.equal(source.phase);
            expect(result.currentPlayers).to.deep.equal(source.currentPlayers);
            expect(wrapper.toSave(result)).to.equal(result);
            expect(result.newTurn).to.equal(true);
            expect(result.log[result.log.length - 1].type).to.equal('event');
            result.players.forEach((p) =>
                expect(p.availableMoves).to.deep.equal(
                    result.currentPlayers.includes(p.id) ? availableMoves(result, p) : null
                )
            );
            expect(
                wrapper.createAnalysisScenario(result, { seed: 'resampled' }).players.map((p) => p.money)
            ).to.deep.equal(result.players.map((p) => p.money));
        });

    it('rejects malformed values, mixed buffers, tentative states and invalid actors without mutation', async () => {
        const source = setup();
        const actor = source.currentPlayers[0];
        for (const value of [-1, 1.2, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1, MAX_ANALYSIS_MONEY + 1, '10', null]) {
            const before = cloneDeep(source);
            await rejects(() => wrapper.analysisMove(source, command(0, value as number), actor));
            expect(source).to.deep.equal(before);
        }
        for (const target of [-1, 3, 0.5, NaN])
            await rejects(() => wrapper.analysisMove(source, command(target, 10), actor));
        for (const invalid of [-1, 3, 0.5, source.players.find((p) => !source.currentPlayers.includes(p.id))!.id])
            await rejects(() => wrapper.analysisMove(source, command(0, 10), invalid));
        await rejects(() => wrapper.analysisMove(source, { name: 'SetAnalysisMoney', data: null } as any, actor));
        for (const input of [
            [command(0, 10), { name: MoveName.Pass, data: true }],
            [command(0, 10), command(1, 20)],
        ])
            await rejects(() => wrapper.analysisMove(source, input as any, actor));
        await rejects(() => wrapper.analysisMove({ ...source, newTurn: false }, command(0, 10), actor));
        await rejects(() => wrapper.analysisMove({ ...source, phase: Phase.GameEnd }, command(0, 10), actor));
    });

    it('rejects live wrapper and engine calls before mutation, including mixed buffers', async () => {
        const source = setup();
        const before = cloneDeep(source);
        const actor = source.currentPlayers[0];
        for (const input of [command(0, 10), [command(0, 10)], [{ name: MoveName.Pass, data: true }, command(0, 10)]]) {
            await rejects(() => wrapper.move(source, input as any, actor));
            expect(source).to.deep.equal(before);
        }
        expect(() => engine.move(source, command(0, 10) as unknown as Move, actor)).to.throw();
        expect(source).to.deep.equal(before);
    });

    it('protects outstanding bids and clears stale powering checkpoints', async () => {
        let state = setup();
        state = await wrapper.analysisMove(
            state,
            { name: MoveName.ChoosePowerPlant, data: state.actualMarket[0].number },
            state.currentPlayers[0]
        );
        const bidder = state.currentPlayers[0];
        state = await wrapper.analysisMove(state, { name: MoveName.Bid, data: 20 }, bidder);
        await rejects(() => wrapper.analysisMove(state, command(bidder, 19), state.currentPlayers[0]));
        expect(
            (await wrapper.analysisMove(state, command(bidder, 20), state.currentPlayers[0])).players[bidder].money
        ).to.equal(20);
        state.phase = Phase.Bureaucracy;
        rememberPowering(state, bidder);
        expect(state.poweringChoices).not.to.equal(undefined);
        const result = await wrapper.analysisMove(state, command(bidder, 30), state.currentPlayers[0]);
        expect(result.poweringChoices).to.equal(undefined);
        expect(result.revisedPowering).to.equal(undefined);
        expect(state.poweringChoices).not.to.equal(undefined);
    });

    it('spends edited money normally and replays edit events in both reconstruction paths', async () => {
        let state = setup();
        const actor = state.currentPlayers[0];
        const beforeEdit = state.log.length;
        state = await wrapper.analysisMove(state, [command(actor, 100)], actor);
        expect(wrapper.replay(state, { to: beforeEdit }).players[actor].money).to.equal(50);
        expect(engine.reconstructState(state).players[actor].money).to.equal(100);
        state = await wrapper.analysisMove(
            state,
            { name: MoveName.ChoosePowerPlant, data: state.actualMarket[0].number },
            actor
        );
        state = await wrapper.analysisMove(state, { name: MoveName.Bid, data: 80 }, actor);
        while (state.chosenPowerPlant)
            state = await wrapper.analysisMove(state, { name: MoveName.Pass, data: true }, state.currentPlayers[0]);
        expect(state.players[actor].money).to.be.lessThan(100);
        expect(wrapper.replay(state).players[actor].money).to.equal(state.players[actor].money);
        expect(engine.reconstructState(state).players[actor].money).to.equal(state.players[actor].money);
    });
});
