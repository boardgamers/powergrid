import Game from '@/components/Game.vue';
import PlayerBoard from '@/components/PlayerBoard.vue';
import { expect } from 'chai';
import { Phase, setup } from 'powergrid-engine';

const options = (Game as any).options;
function context() {
    const sent: unknown[] = [];
    const ctx: any = {
        G: setup(3, { map: 'Germany', variant: 'original', showMoney: false }, 'phase-settings'),
        preferences: {},
        player: 0,
        settings: {},
        emitter: { emit: (...args: unknown[]) => sent.push(args) },
        sent,
    };
    for (const key of ['autoPassSetting', 'reserveAutoPass', 'showAutoPass', 'canEditAuctionSettings'])
        Object.defineProperty(ctx, key, { get: () => options.computed[key].get.call(ctx) });
    return ctx;
}
describe('phase-specific private auto-pass controls', () => {
    it('names the current phase in each complete localizable label', () => {
        const label = (PlayerBoard as any).options.computed.autoPassLabel.get;
        for (const [autoPassSetting, phase] of [
            ['autoPassBids', 'auction'],
            ['autoPassResources', 'resources'],
            ['autoPassBuilding', 'building'],
        ]) {
            expect(label.call({ autoPassSetting })).to.equal(`Auto-pass if unaffordable (${phase})`);
        }
    });
    it('offers only the current phase setting and emits no move', () => {
        const ctx = context();
        for (const [phase, setting] of [
            [Phase.Auction, 'autoPassBids'],
            [Phase.Resources, 'autoPassResources'],
            [Phase.Building, 'autoPassBuilding'],
        ]) {
            ctx.G.phase = phase;
            expect(ctx.showAutoPass).to.equal(true);
            expect(ctx.autoPassSetting).to.equal(setting);
            options.methods.toggleAutoPass.call(ctx);
            expect(ctx.sent.pop()).to.deep.equal(['update:setting', { name: setting, value: true }]);
            ctx.settings[setting] = true;
            options.methods.toggleAutoPass.call(ctx);
            expect(ctx.sent.pop()).to.deep.equal(['update:setting', { name: setting, value: false }]);
        }
        ctx.G.phase = Phase.Bureaucracy;
        expect(ctx.showAutoPass).to.equal(false);
        expect(ctx.reserveAutoPass).to.equal(true);
    });
    it('reserves identical player-board offsets when the phase control disappears', () => {
        const ctx = context();
        ctx.adjustedPlayerOrder = [1, 0, 2];
        const offsets = () => [0, 1, 2].map((index) => options.methods.playerBoardOffset.call(ctx, index));
        ctx.G.phase = Phase.Auction;
        const initial = offsets();
        expect(initial).to.deep.equal([0, 110, 256]);
        for (const phase of [Phase.Resources, Phase.Building, Phase.Bureaucracy]) {
            ctx.G.phase = phase;
            expect(offsets()).to.deep.equal(initial);
        }
        expect(ctx.showAutoPass).to.equal(false);
        options.methods.toggleAutoPass.call(ctx);
        expect(ctx.sent).to.deep.equal([]);
    });
    it('hides settings from spectators, tutorials and analysis; locks public money', () => {
        for (const patch of [
            { player: null },
            { player: 99 },
            { tutorialMove: () => {} },
            { preferences: { analysis: true } },
            { settings: null },
        ]) {
            const ctx = Object.assign(context(), patch);
            expect(ctx.showAutoPass).to.equal(false);
        }
        for (const patch of [
            { paused: true },
            { roundPlan: {} },
            { interactionDisabled: true },
            { gameIsOver: true },
        ]) {
            const ctx = Object.assign(context(), patch);
            options.methods.toggleAutoPass.call(ctx);
            expect(ctx.sent).to.deep.equal([]);
        }
        const ctx = context();
        ctx.G.options.showMoney = true;
        expect(ctx.showAutoPass).to.equal(true);
        expect(ctx.canEditAuctionSettings).to.equal(false);
        options.methods.toggleAutoPass.call(ctx);
        expect(ctx.sent).to.deep.equal([]);
    });
});
