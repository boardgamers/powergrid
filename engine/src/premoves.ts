import assert from 'assert';
import { isEqual } from 'lodash';
import { availableMoves } from './available-moves';
import { move as play } from './engine';
import { GameState, Phase } from './gamestate';
import { Move, MoveName, Moves } from './move';
import { copyState, nextPlanningPhase, planningPhase, roundPhases } from './planning';

export interface PhasePlan {
    phase: Phase.Building | Phase.Bureaucracy;
    moves: Move[];
}
export interface PremovePlan {
    round: number;
    revision: number;
    requestId: string;
    phases: PhasePlan[];
    notice?: string;
}
export interface AutomationState {
    version: 1;
    plans: Record<number, PremovePlan>;
    increments: number[];
    liveUpdate: boolean;
}
export interface PremoveCommand {
    type: 'premoves';
    round: number;
    revision: number;
    requestId: string;
    phases: PhasePlan[];
}
export const automation = (G: GameState): AutomationState =>
    G.automation ||
    (G.automation = {
        version: 1,
        plans: {},
        increments: G.players.map(() => 0),
        liveUpdate: false,
    });
export function isPremoveCommand(value: unknown): value is PremoveCommand {
    return !!value && typeof value === 'object' && (value as PremoveCommand).type === 'premoves';
}
export function canManagePremoves(G: GameState, seat: number): boolean {
    return !!G.players[seat] && !G.players[seat].isDropped && G.phase !== Phase.GameEnd;
}
/** Resource and plant purchases are only simulated; queueing starts after resource buying. */
export function canQueuePhases(G: GameState, seat: number, phases: PhasePlan[]): boolean {
    const next = nextPlanningPhase(G, seat);
    if (!next || roundPhases.indexOf(next) < roundPhases.indexOf(Phase.Building)) return false;
    return phases.every((p) => roundPhases.indexOf(p.phase) >= roundPhases.indexOf(next));
}
function resolveMove(G: GameState, seat: number, move: Move): Move {
    const offered = availableMoves(G, G.players[seat])[move.name];
    if (move.name === MoveName.Build) {
        const intended = move as Moves.MoveBuild;
        assert(Number.isFinite(intended.data.price) && intended.data.price >= 0, 'Invalid city price.');
        const actual = (offered as Moves.MoveBuild['data'][] | undefined)?.find(
            (p) => p.name === intended.data.name && !!p.freeJump === !!intended.data.freeJump
        );
        assert(actual, `${intended.data.name} is no longer available or affordable.`);
        assert(
            actual.price === intended.data.price,
            `${intended.data.name} now costs $${actual.price}, instead of the planned $${intended.data.price}.`
        );
        return { name: MoveName.Build, data: copyState(actual) };
    }
    assert(
        offered?.some((value) => isEqual(value, move.data)),
        move.name === MoveName.UsePowerPlant
            ? 'The selected power plant or fuel is no longer available.'
            : 'This phase can no longer finish as planned.'
    );
    return { name: move.name, data: copyState(move.data) } as Move;
}
function validateShape(phases: PhasePlan[]) {
    assert(Array.isArray(phases) && phases.length <= 2, 'Queue at most building and powering for this round.');
    let previous = -1;
    for (const phase of phases) {
        const index = [Phase.Building, Phase.Bureaucracy].indexOf(phase.phase);
        assert(index > previous, 'Queued phases must be building, then powering, without duplicates.');
        previous = index;
        assert(Array.isArray(phase.moves) && phase.moves.length > 0 && phase.moves.length <= 64, 'Invalid phase plan.');
        phase.moves.forEach((move, i) => {
            const expected =
                i === phase.moves.length - 1
                    ? MoveName.Pass
                    : phase.phase === Phase.Building
                    ? MoveName.Build
                    : MoveName.UsePowerPlant;
            assert(
                move && move.name === expected,
                'Finish each phase with Done. Only cities and powering can be queued.'
            );
        });
    }
}
export function setPremoves(G: GameState, command: PremoveCommand, seat: number) {
    assert(canManagePremoves(G, seat), 'You cannot queue moves in this game.');
    const state = automation(G);
    const old = state.plans[seat];
    assert(
        typeof command.requestId === 'string' && command.requestId.length > 0 && command.requestId.length <= 100,
        'Invalid request.'
    );
    if (old?.requestId === command.requestId) {
        state.liveUpdate = true;
        G.newTurn = true;
        return;
    }
    assert(command.round === G.round, 'The round changed. Start a new plan.');
    assert(command.revision === (old?.revision || 0), 'Your queue changed. Refresh it before editing.');
    validateShape(command.phases);
    if (command.phases.length) {
        assert(canQueuePhases(G, seat, command.phases), 'Finish buying resources before queueing cities or powering.');
        const probe = copyState(G);
        for (const phase of command.phases) {
            planningPhase(probe, seat, phase.phase);
            for (const move of phase.moves.slice(0, -1)) {
                const resolved = resolveMove(probe, seat, move);
                probe.players[seat].availableMoves = availableMoves(probe, probe.players[seat]);
                // Validate against known costs without drawing or inspecting hidden plants.
                play(probe, resolved, seat, { updateBuildingMarket: false });
            }
            resolveMove(probe, seat, phase.moves[phase.moves.length - 1]);
        }
    }
    state.plans[seat] = {
        round: G.round,
        revision: (old?.revision || 0) + 1,
        requestId: command.requestId,
        phases: copyState(command.phases).map((p) => ({
            phase: p.phase,
            moves: p.moves.map((m) => ({ name: m.name, data: m.data } as Move)),
        })),
    };
    state.liveUpdate = true;
    G.newTurn = true;
}
/** Manual decisions replace that queued phase, preserving later phases. */
export function reconcileManualPlan(G: GameState, seat: number, phase: Phase) {
    const plan = automation(G).plans[seat];
    if (!plan?.phases.some((p) => p.phase === phase)) return;
    plan.phases = plan.phases.filter((p) => roundPhases.indexOf(p.phase) > roundPhases.indexOf(phase));
    plan.revision++;
    plan.notice = 'Your manual moves replaced the queued plan for this phase.';
}
export function runPremoves(initial: GameState, serverTime?: number): GameState {
    let G = initial;
    for (let guard = 0; guard < G.players.length * 3 + 1; guard++) {
        const state = automation(G);
        for (const [id, plan] of Object.entries(state.plans)) {
            if (
                plan.phases.length &&
                (plan.round !== G.round || G.phase === Phase.GameEnd || G.players[+id].isDropped)
            ) {
                plan.phases = [];
                plan.revision++;
                plan.notice = 'The queued plan ended with the round.';
            }
        }
        const seat = G.currentPlayers.find((id) => {
            const phase = state.plans[id]?.phases[0];
            return phase && roundPhases.indexOf(phase.phase) <= roundPhases.indexOf(G.phase);
        });
        if (seat === undefined) break;
        const plan = state.plans[seat];
        const phase = plan.phases[0];
        try {
            assert(phase.phase === G.phase, 'The planned phase has already passed.');
            let probe = copyState(G);
            let increments = 0;
            for (const move of phase.moves) {
                const resolved = resolveMove(probe, seat, move);
                probe.players[seat].availableMoves = availableMoves(probe, probe.players[seat]);
                probe = play(probe, { ...resolved, serverTime }, seat);
                if (probe.newTurn !== false) increments++;
            }
            const completed = automation(probe).plans[seat];
            completed.phases.shift();
            completed.revision++;
            completed.notice =
                phase.phase === Phase.Building
                    ? 'Your queued cities were built.'
                    : 'Your queued plants powered cities.';
            automation(probe).increments[seat] += increments;
            automation(probe).liveUpdate = false;
            G = probe;
        } catch (error) {
            plan.phases = [];
            plan.revision++;
            plan.notice = `Premoves stopped: ${error instanceof Error ? error.message : String(error)}`;
        }
    }
    return G;
}
