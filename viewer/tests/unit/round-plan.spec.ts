import { expect } from 'chai';
import { MoveName, Phase, setup } from 'powergrid-engine';
import { planMove, startRoundPlan } from 'powergrid-engine/dist/src/planning';
import { completedPhases } from '@/util/round-plan';

describe('round planner queue selection', () => {
    it('queues only complete building and powering phases, excluding assumed purchases', () => {
        const base = setup(3, { map: 'Germany' }, 'budget');
        base.players[0].money = 70;
        let plan = startRoundPlan(base, 0);
        plan = planMove(plan, { name: MoveName.ChoosePowerPlant, data: 3 });
        plan = planMove(plan, { name: MoveName.Bid, data: 15 });
        const buy = plan.state.players[0].availableMoves!.BuyResource!.find((m) => m.resource === 'oil')!;
        plan = planMove(plan, { name: MoveName.BuyResource, data: { resource: buy.resource } });
        plan = planMove(plan, { name: MoveName.BuyResource, data: { resource: buy.resource } });
        const resources = 55 - plan.state.players[0].money;
        plan = planMove(plan, { name: MoveName.Pass, data: true });
        const city = plan.state.players[0].availableMoves!.Build![0];
        plan = planMove(plan, { name: MoveName.Build, data: city });
        expect(completedPhases(plan)).to.have.length(0);
        plan = planMove(plan, { name: MoveName.Pass, data: true });
        expect(completedPhases(plan).map((p) => p.phase)).to.deep.equal([Phase.Building]);
        const use = plan.state.players[0].availableMoves!.UsePowerPlant![0];
        plan = planMove(plan, { name: MoveName.UsePowerPlant, data: use });
        plan = planMove(plan, { name: MoveName.Pass, data: true });
        expect(plan.state.players[0].money).to.equal(67 - resources);
        expect(completedPhases(plan).map((p) => p.phase)).to.deep.equal([Phase.Building, Phase.Bureaucracy]);
        expect(base.players[0].money).to.equal(70);
    });
});
