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

    it('retains the standard and alternate deck lookup for discarded cards', () => {
        for (const alternatePowerPlants of [false, true]) {
            const state = setup(3, { map: 'Germany', alternatePowerPlants }, 'journal');
            state.actualMarket = [];
            state.futureMarket = [];
            expect(journalPlant(state, 18)).to.deep.equal(getPowerPlant(18, 'Germany', alternatePowerPlants));
        }
    });
});
