import { expect } from 'chai';
import { setup } from 'powergrid-engine';
import { getPowerPlant } from 'powergrid-engine/src/engine';
import { journalPlant } from '../../src/util/journal-plant';

describe('journal plant illustrations', () => {
    it('matches every regional card, including cards no longer on the board', () => {
        const state = setup(5, { map: 'Northern Europe', variant: 'recharged' }, 'journal');
        for (const region of Object.keys(state.map.regionalPowerPlants!)) {
            state.map.cities = [{ ...state.map.cities[0], region }];
            state.actualMarket = [];
            state.futureMarket = [];
            state.players.forEach((player) => (player.powerPlants = []));
            for (const plant of state.map.regionalPowerPlants![region]) {
                expect(journalPlant(state, plant.number)).to.deep.equal(plant);
                state.players[0].powerPlants = [plant];
                expect(journalPlant(state, plant.number)).to.deep.equal(plant);
                state.players[0].powerPlants = [];
            }
        }
    });

    it("looks up discarded cards in the game's deck", () => {
        for (const powerPlantDeck of ['standard', 'deck1', 'deck2'] as const) {
            const state = setup(3, { map: 'Germany', powerPlantDeck }, 'journal');
            state.actualMarket = [];
            state.futureMarket = [];
            expect(journalPlant(state, 20)).to.deep.equal(getPowerPlant(20, 'Germany', powerPlantDeck));
        }
    });

    it("finds each copy of a shuffled deck's plant number", () => {
        const state = setup(3, { map: 'USA', powerPlantDeck: 'shuffled' }, 'journal');
        state.actualMarket = [];
        state.futureMarket = [];
        for (const number of [46, 46.1, 46.2]) {
            expect(journalPlant(state, number)).to.deep.equal(getPowerPlant(number, 'USA', 'shuffled'));
        }
        expect(journalPlant(state, 46.2)!.type).to.not.equal(journalPlant(state, 46)!.type);
    });

    it('reads the legacy alternate deck flag where it applied', () => {
        const state = setup(3, { map: 'Europe', alternatePowerPlants: true }, 'journal');
        state.actualMarket = [];
        state.futureMarket = [];
        expect(journalPlant(state, 20)).to.deep.equal(getPowerPlant(20, 'Europe', 'deck2'));
    });
});
