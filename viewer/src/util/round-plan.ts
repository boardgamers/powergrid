import { Phase, MoveName, Move } from 'powergrid-engine';
import type { RoundPlan } from 'powergrid-engine/src/planning';
import type { PhasePlan } from 'powergrid-engine/src/premoves';

export function completedPhases(plan: RoundPlan): PhasePlan[] {
    return [Phase.Building, Phase.Bureaucracy].flatMap((phase) => {
        const moves = plan.entries.filter((e) => e.phase === phase).map((e) => e.move);
        return moves.length && moves[moves.length - 1].name === MoveName.Pass
            ? [{ phase: phase as Phase.Building | Phase.Bureaucracy, moves }]
            : [];
    });
}
export function describeMove(move: Move): string {
    switch (move.name) {
        case MoveName.Build:
            return `${move.data.name} · up to $${move.data.price}`;
        case MoveName.UsePowerPlant:
            return `Plant ${move.data.powerPlant}${
                move.data.resourcesSpent.length ? ' · ' + move.data.resourcesSpent.join(', ') : ' · no fuel'
            }`;
        case MoveName.Pass:
            return 'Finish phase';
        case MoveName.ChoosePowerPlant:
            return `Consider plant ${move.data}`;
        case MoveName.Bid:
            return `Assume purchase for $${move.data}`;
        case MoveName.BuyResource:
            return `Buy ${move.data.resource}`;
        case MoveName.DiscardPowerPlant:
            return `Discard plant ${move.data}`;
        case MoveName.DiscardResources:
            return `Discard ${move.data}`;
        default:
            return move.name;
    }
}
