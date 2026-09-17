import assert from 'assert';
import { isEqual } from 'lodash';
import { availableMoves } from './available-moves';
import { calculateMaxCitiesPowered, endAuction, move as play, powerIncome } from './engine';
import { GameState, Phase } from './gamestate';
import { Move, MoveName } from './move';

export const roundPhases = [Phase.Auction, Phase.Resources, Phase.Building, Phase.Bureaucracy];
export const copyState = <T>(value: T): T => JSON.parse(JSON.stringify(value));
export interface PlannedMove {
    phase: Phase;
    move: Move;
}
export interface RoundPlan {
    state: GameState;
    seat: number;
    entries: PlannedMove[];
    startPhase: Phase;
    income: number;
    finished: boolean;
    finalScoring?: boolean;
}

/** Earliest phase this player still has to play, regardless of whose turn it is. */
export function nextPlanningPhase(G: GameState, seat: number): Phase | undefined {
    const player = G.players[seat];
    if (!player || player.isDropped || player.money < 0) return;
    let index = roundPhases.indexOf(G.phase);
    if (index < 0) return;
    if (G.phase === Phase.Auction ? player.skipAuction : player.passed) index++;
    return roundPhases[index];
}

function updatePlanningMoves(G: GameState, seat: number) {
    const player = G.players[seat];
    player.availableMoves = availableMoves(G, player);
    // Done can simulate skipping a plant, including before mandatory round-one buying.
    if (
        G.phase === Phase.Auction &&
        !player.availableMoves.DiscardPowerPlant &&
        !player.availableMoves.DiscardResources
    ) {
        player.availableMoves.Pass = [true];
    }
}

/** Only the player's own decisions are simulated. No guessed opponent moves or deck draws. */
export function planningPhase(G: GameState, seat: number, phase: Phase): GameState {
    const previous = G.phase;
    G.phase = phase;
    G.currentPlayers = [seat];
    G.newTurn = true;
    G.players.forEach((p) => {
        p.availableMoves = null;
        p.clockStartedAt = undefined;
    });
    const player = G.players[seat];
    player.passed = false;
    if (phase !== Phase.Auction) {
        G.chosenPowerPlant = undefined;
        G.currentBid = undefined;
    }
    if (phase === Phase.Resources && (previous !== phase || !player.availableMoves)) {
        // A side/resource choice is only ours when we were already the active buyer.
        G.chosenResource = undefined;
        G.chosenSide = undefined;
    }
    if (phase === Phase.Bureaucracy && previous !== phase) {
        player.powerPlantsNotUsed = player.powerPlants.map((p) => p.number);
        player.citiesPowered = 0;
        player.resourcesUsed = [];
        player.targetCitiesPowered = calculateMaxCitiesPowered(G, player);
    }
    updatePlanningMoves(G, seat);
    return G;
}

export function startRoundPlan(base: GameState, seat: number, startPhase?: Phase): RoundPlan {
    const next = nextPlanningPhase(base, seat);
    assert(next, 'You have no more decisions to simulate this round.');
    const phase = startPhase || next!;
    assert(
        roundPhases.includes(phase) && roundPhases.indexOf(phase) >= roundPhases.indexOf(next!),
        'This phase has already passed.'
    );
    const state = copyState(base);
    // Planning must also work from the player's public, stripped state.
    state.powerPlantsDeck = [];
    state.hiddenLog = [];
    delete state.automation;
    const ownResourceTurn = base.phase === Phase.Resources && base.currentPlayers.includes(seat);
    planningPhase(state, seat, phase);
    if (ownResourceTurn) {
        state.chosenResource = base.chosenResource;
        state.chosenSide = base.chosenSide;
        state.players[seat].availableMoves = availableMoves(state, state.players[seat]);
    }
    const plan: RoundPlan = {
        state,
        seat,
        entries: [],
        startPhase: phase,
        income: 0,
        finished: false,
    };
    if (phase === Phase.Bureaucracy) finishFinalRound(plan);
    return plan;
}

/** Final scoring uses maximum power capacity; it does not spend fuel or pay normal income. */
function finishFinalRound(plan: RoundPlan): boolean {
    const G = plan.state;
    if (!G.players.some((p) => p.cities.length >= G.citiesToEndGame)) return false;
    const player = G.players[plan.seat];
    player.citiesPowered = calculateMaxCitiesPowered(G, player);
    if (G.map.name === 'India' && G.citiesBuiltInCurrentRound! > G.players.length * 2) {
        plan.income = powerIncome(G, player);
        player.money += plan.income;
    }
    plan.finalScoring = plan.finished = true;
    G.phase = Phase.GameEnd;
    G.currentPlayers = [];
    player.availableMoves = null;
    return true;
}

function nextPhase(plan: RoundPlan) {
    if (plan.state.phase === Phase.Building && finishFinalRound(plan)) return;
    const phase = roundPhases[roundPhases.indexOf(plan.state.phase) + 1];
    assert(phase, 'The simulation ends after powering cities.');
    planningPhase(plan.state, plan.seat, phase);
}

export function planMove(previous: RoundPlan, input: Move): RoundPlan {
    assert(!previous.finished, 'The simulation ends after powering cities.');
    const plan = copyState(previous);
    const G = plan.state;
    const player = G.players[plan.seat];
    const phase = G.phase;
    const move = copyState(input);
    delete move.time;
    delete move.serverTime;
    const offered = player.availableMoves && player.availableMoves[move.name];
    // Skipping an auction is a hypothetical choice, including mandatory round-one buying.
    const skipPlant =
        phase === Phase.Auction &&
        move.name === MoveName.Pass &&
        !player.availableMoves?.DiscardPowerPlant &&
        !player.availableMoves?.DiscardResources;
    assert(
        skipPlant || offered?.some((value) => isEqual(value, move.data)),
        'This move is not affordable or available.'
    );

    if (phase === Phase.Auction && move.name === MoveName.ChoosePowerPlant) {
        G.chosenPowerPlant = G.actualMarket.find((p) => p.number === move.data)!;
        G.auctioningPlayer = plan.seat;
        G.currentBid = undefined;
        G.minimunBid =
            G.options.variant === 'recharged' && G.plantDiscountActive && G.actualMarket[0].number === move.data
                ? 1
                : Number(move.data);
    } else if (phase === Phase.Auction && move.name === MoveName.Bid) {
        // The entered bid is an assumed winning price, never a real bid.
        endAuction(G, player, Number(move.data));
        G.pendingMarketRefill = false;
        player.availableMoves = availableMoves(G, player);
        if (!player.availableMoves.DiscardPowerPlant && !player.availableMoves.DiscardResources) nextPhase(plan);
    } else if (move.name === MoveName.Pass) {
        if (phase === Phase.Bureaucracy) {
            plan.income = powerIncome(G, player);
            player.money += plan.income;
            plan.finished = true;
            G.currentPlayers = [];
            player.availableMoves = null;
        } else nextPhase(plan);
    } else {
        // Reuse all normal affordability, storage, hybrid-fuel and connection rules.
        play(G, move, plan.seat, { updateBuildingMarket: false });
        if (phase === Phase.Auction) {
            G.phase = Phase.Auction;
            player.availableMoves = availableMoves(G, player);
            if (!player.availableMoves.DiscardPowerPlant && !player.availableMoves.DiscardResources) nextPhase(plan);
        }
    }
    if (!plan.finished) {
        G.currentPlayers = [plan.seat];
        updatePlanningMoves(G, plan.seat);
    }
    // Normal move bookkeeping derives these from the hidden deck, absent in a viewer.
    // No draw is predicted in a plan, so keep its public deck indicator unchanged.
    G.cardsLeft = previous.state.cardsLeft;
    G.nextCardWeak = previous.state.nextCardWeak;
    plan.entries.push({ phase, move });
    return plan;
}

export function replayRoundPlan(base: GameState, seat: number, entries: PlannedMove[], startPhase?: Phase): RoundPlan {
    let plan = startRoundPlan(base, seat, startPhase);
    for (const entry of entries) {
        assert(entry.phase === plan.state.phase, 'The live game has moved to another phase. Start a new simulation.');
        plan = planMove(plan, entry.move);
    }
    return plan;
}
