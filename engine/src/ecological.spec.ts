import { expect } from 'chai';
import { range } from 'lodash';
import { init, moveAI, replay } from '../wrapper';
import { addPowerPlant, getPowerPlant, reconstructionOptions, setup } from './engine';
import { GameState, PowerPlant, PowerPlantType, Variant } from './gamestate';
import { FUSION_IS_ECOLOGICAL, isEcological } from './powerPlants';

// Pending step messages are an outbound queue the wrapper drains, and replay clears it.
const json = (G: GameState) => {
    const copy = JSON.parse(JSON.stringify(G));
    delete copy.pendingMessages;
    return copy;
};

function playAI(G: GameState, moves: number): GameState {
    for (let i = 0; i < moves && G.currentPlayers.length > 0; i++) G = moveAI(G, G.currentPlayers[0]);
    return G;
}

const allPlants = (G: GameState) => [...G.actualMarket, ...G.futureMarket, ...G.powerPlantsDeck].map((pp) => pp.number);

const variants: Variant[] = ['original', 'recharged'];

describe('ecological power plants', () => {
    it('counts wind plants as ecological, and fusion plants only under the ruling', () => {
        expect(FUSION_IS_ECOLOGICAL).to.equal(false);
        expect(isEcological(getPowerPlant(13), false)).to.equal(true);
        expect(isEcological(getPowerPlant(50), false)).to.equal(false);
        expect(isEcological(getPowerPlant(50), true)).to.equal(true);
        expect(isEcological(getPowerPlant(11), true)).to.equal(false);
    });

    it('stores the ruling only on the maps with ecological rules', async () => {
        for (const variant of variants) {
            for (const map of ['Benelux', 'Quebec'] as const) {
                const G = await init(4, [], { map, variant }, 'eco');
                expect(G.options.fusionEcological).to.equal(false);
            }
            for (const map of ['Germany', 'France'] as const) {
                const G = await init(4, [], { map, variant }, 'eco');
                expect(G.options).to.not.have.property('fusionEcological');
            }
        }
    });

    it('lets Québec remove fusion plant 50 at setup, unless fusion is ecological', () => {
        for (const variant of variants) {
            const seeds = range(40).map(String);
            const without50 = seeds.filter(
                (seed) => !allPlants(setup(2, { map: 'Quebec', variant }, seed)).includes(50)
            );
            expect(without50, variant).to.not.be.empty;

            for (const seed of seeds) {
                const G = setup(2, { map: 'Quebec', variant, fusionEcological: true }, seed);
                expect(allPlants(G), `${variant} ${seed}`).to.include(50);
            }
        }
    });

    it('replays Québec games created before the ruling with fusion protected', () => {
        for (const variant of variants) {
            const legacyOptions = reconstructionOptions({ map: 'Quebec', variant });
            for (const seed of range(40).map(String)) {
                expect(allPlants(setup(2, legacyOptions, seed)), `${variant} ${seed}`).to.include(50);
            }

            const legacy = playAI(setup(3, legacyOptions, 'old'), 60);
            expect(legacy.options).to.not.have.property('fusionEcological');
            expect(legacy.options).to.not.have.property('legacyEcological');
            expect(json(replay(legacy))).to.deep.equal(json(legacy));

            const current = playAI(setup(3, { map: 'Quebec', variant }, 'new'), 60);
            expect(current.options.fusionEcological).to.equal(false);
            expect(json(replay(current))).to.deep.equal(json(current));
        }
    });

    it('adds a fusion plant to the Benelux market only under the ruling', () => {
        // A fusion plant numbered low enough to be the smallest in the future market.
        const fusion: PowerPlant = { number: 30, type: PowerPlantType.Nuclear, cost: 0, citiesPowered: 6 };
        for (const fusionEcological of [false, true]) {
            const G = setup(3, { map: 'Benelux', variant: 'recharged', fusionEcological }, 'benelux');
            G.actualMarket = [20, 21, 23, 24].map((n) => getPowerPlant(n));
            G.futureMarket = [39, 40, 42].map((n) => getPowerPlant(n));
            G.powerPlantsDeck = [fusion];
            addPowerPlant(G);
            expect(G.actualMarket.map((pp) => pp.number)).to.deep.equal(
                fusionEcological ? [20, 21, 23, 24, 30] : [20, 21, 23, 24]
            );
        }
    });
});
