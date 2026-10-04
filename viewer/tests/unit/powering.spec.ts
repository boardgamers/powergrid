import { expect } from 'chai';
import { availableMoves, move, MoveName, Phase, setup } from 'powergrid-engine';
import { powerPlants } from 'powergrid-engine/src/powerPlants';
import { canAutoFinishPowering, freePlantMoves, poweredCities } from '../../src/util/powering';

function position(map: 'Germany' | 'Australia' | 'India' = 'Germany') {
    const state = setup(3, { map, variant: 'original' }, 'powering');
    state.phase = Phase.Bureaucracy;
    state.currentPlayers = [0, 1, 2];
    const player = state.players[0];
    player.powerPlants = [27, 20, 26].map((number) => ({ ...powerPlants.find((plant) => plant.number === number)! }));
    player.powerPlantsNotUsed = [27, 20, 26];
    player.cities = state.map.cities.slice(0, 8).map((city) => ({ name: city.name, position: 0 }));
    player.coalLeft = 3;
    player.oilLeft = 0;
    player.passed = false;
    player.availableMoves = availableMoves(state, player);
    return state;
}
function runFree(state: ReturnType<typeof position>) {
    return freePlantMoves(state, 0).reduce((current, action) => move(current, action, 0), state);
}

describe('automatic free plants', () => {
    it('uses only legal zero-fuel activations and keeps a real fuel choice open', () => {
        const initial = position();
        expect(freePlantMoves(initial, 0).map((action) => action.data)).to.deep.equal([
            { powerPlant: 27, resourcesSpent: [], citiesPowered: 3 },
        ]);
        const state = runFree(initial);
        expect(state.players[0].coalLeft).to.equal(3);
        expect(poweredCities(state, state.players[0])).to.equal(3);
        expect(canAutoFinishPowering(state, 0)).to.equal(false);
        expect(freePlantMoves(state, 0)).to.deep.equal([]);
    });
    it('finishes when free output covers all cities without burning stored fuel', () => {
        const initial = position();
        initial.players[0].cities = initial.players[0].cities.slice(0, 2);
        const state = runFree(initial);
        expect(poweredCities(state, state.players[0])).to.equal(2);
        expect(canAutoFinishPowering(state, 0)).to.equal(true);
        expect(state.players[0].coalLeft).to.equal(3);
    });
    it('finishes after free plants when the other plants lack fuel', () => {
        const state = position();
        state.players[0].coalLeft = 0;
        state.players[0].availableMoves = availableMoves(state, state.players[0]);
        expect(canAutoFinishPowering(runFree(state), 0)).to.equal(true);
    });
    it('keeps the powered count after income is collected', () => {
        let state = runFree(position());
        state = move(state, { name: MoveName.Pass, data: true }, 0);
        expect(state.players[0].citiesPowered).to.equal(0);
        expect(poweredCities(state, state.players[0])).to.equal(3);
        expect(freePlantMoves(state, 0)).to.deep.equal([]);
        expect(canAutoFinishPowering(state, 0)).to.equal(false);
    });
    it('handles multiple free plants including fusion without consuming fuel', () => {
        const state = position();
        state.players[0].powerPlants = [27, 50].map((number) => ({
            ...powerPlants.find((plant) => plant.number === number)!,
        }));
        state.players[0].powerPlantsNotUsed = [27, 50];
        state.players[0].availableMoves = availableMoves(state, state.players[0]);
        expect(freePlantMoves(state, 0)).to.have.length(2);
        expect(canAutoFinishPowering(runFree(state), 0)).to.equal(true);
    });
    it('never treats an Australian uranium mine as a city-powering plant', () => {
        const state = position('Australia');
        state.players[0].powerPlants.push({ ...powerPlants.find((plant) => plant.number === 11)! });
        state.players[0].availableMoves = availableMoves(state, state.players[0]);
        expect(poweredCities(state, state.players[0])).to.equal(0);
        expect(freePlantMoves(state, 0)).to.have.length(1);
    });
    it('respects India’s required output and legal Pass', () => {
        const state = position('India');
        state.players[0].targetCitiesPowered = 8;
        state.players[0].availableMoves = availableMoves(state, state.players[0]);
        const after = runFree(state);
        expect(after.players[0].availableMoves!.Pass).to.equal(undefined);
        expect(canAutoFinishPowering(after, 0)).to.equal(false);
    });
    it('does nothing outside the powering phase', () => {
        const state = position();
        state.phase = Phase.Building;
        expect(freePlantMoves(state, 0)).to.deep.equal([]);
        expect(canAutoFinishPowering(state, 0)).to.equal(false);
    });
});
