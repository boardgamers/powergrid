import { MoveName, Phase } from 'powergrid-engine';
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
