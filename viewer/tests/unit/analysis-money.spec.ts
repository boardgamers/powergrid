import Game from '@/components/Game.vue';
import { expect } from 'chai';
import { setup } from 'powergrid-engine';
const options = (Game as any).options;
const valid = (ctx: any) => options.computed.validAnalysisMoney.get.call(ctx);
function context() {
    const G = setup(3, { map: 'Germany', variant: 'recharged', showMoney: true }, 'money');
    const sent: any[] = [];
    const ctx: any = {
        $nextTick: () => {},
        G,
        committedState: G,
        preferences: { analysis: true },
        player: G.currentPlayers[0],
        turnMoves: [],
        analysisMoneyTarget: 1,
        analysisMoneyValue: '123',
        analysisMoneyPending: false,
        emitter: { emit: (...args: any[]) => sent.push(args) },
        sent,
    };
    ctx.canEditAnalysisMoney = () => options.methods.canEditAnalysisMoney.call(ctx);
    Object.defineProperty(ctx, 'validAnalysisMoney', { get: () => valid(ctx) });
    return ctx;
}
describe('analysis money editor', () => {
    it('requires an active controlled seat and a clean analysis position', () => {
        expect(context().canEditAnalysisMoney()).to.equal(true);
        for (const patch of [
            { preferences: {} },
            { player: undefined },
            { player: 99 },
            { paused: true },
            { interactionDisabled: true },
            { roundPlan: {} },
            { turnMoves: [{}] },
            { pendingPlanId: 'x' },
            { changingBid: true },
            { poweringSubmitting: true },
            { undoRequested: true },
            { recentLocalUndo: true },
            { analysisMoneyPending: true },
            { tutorialMove: () => {} },
            { committedState: null },
        ]) {
            expect(Object.assign(context(), patch).canEditAnalysisMoney()).to.equal(false);
        }
        const ctx = context();
        ctx.G.currentPlayers = [];
        expect(ctx.canEditAnalysisMoney()).to.equal(false);
        ctx.G.currentPlayers = [ctx.player];
        ctx.G.newTurn = false;
        expect(ctx.canEditAnalysisMoney()).to.equal(false);
    });
    it('validates bounds and outstanding, but not stale, bids', () => {
        const ctx = context();
        for (const value of ['', ' ', '-1', '0.5', '10000', '9007199254740992', 'NaN', 'Infinity']) {
            ctx.analysisMoneyValue = value;
            expect(valid(ctx), value).to.equal(false);
        }
        for (const value of ['0', '9999', '50']) {
            ctx.analysisMoneyValue = value;
            expect(valid(ctx)).to.equal(true);
        }
        ctx.G.players[1].bid = 60;
        ctx.analysisMoneyValue = '50';
        expect(valid(ctx)).to.equal(true);
        ctx.G.chosenPowerPlant = ctx.G.actualMarket[0];
        expect(valid(ctx)).to.equal(false);
        ctx.analysisMoneyValue = '60';
        expect(valid(ctx)).to.equal(true);
    });
    it('emits one standalone command for any seat without changing state or buffer', () => {
        for (const target of [0, 1, 2]) {
            const ctx = context();
            ctx.analysisMoneyTarget = target;
            const before = JSON.stringify(ctx.G);
            options.methods.saveAnalysisMoney.call(ctx);
            options.methods.saveAnalysisMoney.call(ctx);
            expect(ctx.sent).to.deep.equal([
                ['move', [{ name: 'SetAnalysisMoney', data: { player: target, money: 123 } }]],
            ]);
            expect(JSON.stringify(ctx.G)).to.equal(before);
            expect(ctx.turnMoves).to.deep.equal([]);
        }
    });
    it('explicitly refreshes after silent host failure without retrying or unlocking locally', () => {
        const ctx = context();
        ctx.cancelAnalysisMoney = () => options.methods.cancelAnalysisMoney.call(ctx);
        const before = JSON.stringify(ctx.G);
        options.methods.saveAnalysisMoney.call(ctx);
        // Actual BGS rejection sends neither move:result nor state.
        options.methods.closeAnalysisMoney.call(ctx);
        expect(ctx.analysisMoneyTarget).to.equal(null);
        expect(ctx.analysisMoneyPending).to.equal(true);
        expect(ctx.canEditAnalysisMoney()).to.equal(false);
        expect(ctx.sent).to.deep.equal([
            ['move', [{ name: 'SetAnalysisMoney', data: { player: 1, money: 123 } }]],
            ['fetchState'],
        ]);
        expect(JSON.stringify(ctx.G)).to.equal(before);
        expect(ctx.turnMoves).to.deep.equal([]);
    });
    it('cancels an unsent edit without refreshing', () => {
        const ctx = context();
        ctx.cancelAnalysisMoney = () => options.methods.cancelAnalysisMoney.call(ctx);
        options.methods.closeAnalysisMoney.call(ctx);
        expect(ctx.analysisMoneyTarget).to.equal(null);
        expect(ctx.sent).to.deep.equal([]);
    });
    it('does not submit invalid or stale dialogs and unlocks only matching rejected commands', () => {
        const ctx = context();
        ctx.analysisMoneyValue = '-1';
        options.methods.saveAnalysisMoney.call(ctx);
        expect(ctx.sent).to.have.length(0);
        ctx.analysisMoneyValue = '50';
        ctx.preferences.analysis = false;
        options.methods.saveAnalysisMoney.call(ctx);
        expect(ctx.sent).to.have.length(0);
        ctx.analysisMoneyPending = true;
        options.methods.onAnalysisMoneyResult.call(ctx, { ok: false, move: [{ name: 'Pass' }] });
        expect(ctx.analysisMoneyPending).to.equal(true);
        options.methods.onAnalysisMoneyResult.call(ctx, { ok: false, move: [{ name: 'SetAnalysisMoney' }] });
        expect(ctx.analysisMoneyPending).to.equal(false);
        expect(ctx.analysisMoneyError).to.be.a('string');
    });
});
