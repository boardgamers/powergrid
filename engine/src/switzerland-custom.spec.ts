import { expect } from 'chai';
import { alpineBonusLeft, availableMoves } from './available-moves';
import { calculateMaxCitiesPowered, setup } from './engine';
import { GameState, Phase, Player, PowerPlant, PowerPlantType } from './gamestate';
import { map as switzerland } from './maps/switzerland';
import { MoveName } from './move';

const wind = (number: number, citiesPowered: number): PowerPlant => ({
    number,
    type: PowerPlantType.Wind,
    cost: 0,
    citiesPowered,
});
const coal = (number: number, citiesPowered: number): PowerPlant => ({
    number,
    type: PowerPlantType.Coal,
    cost: 2,
    citiesPowered,
});

/** A Bureaucracy-phase game with the whole Swiss board, and player 0 holding these plants and cities. */
function bureaucracy(plants: PowerPlant[], cities: string[], coalLeft = 0): { G: GameState; player: Player } {
    const G = setup(3, { map: 'SwitzerlandCustom', variant: 'original' }, 'swiss');
    G.map = JSON.parse(JSON.stringify(switzerland));
    G.phase = Phase.Bureaucracy;
    const player = G.players[0];
    player.powerPlants = plants;
    player.powerPlantsNotUsed = plants.map((p) => p.number);
    player.cities = cities.map((name) => ({ name, position: 0 }));
    player.coalLeft = coalLeft;
    return { G, player };
}
const offered = (G: GameState, player: Player) =>
    (availableMoves(G, player)[MoveName.UsePowerPlant] ?? []) as { powerPlant: number; citiesPowered: number }[];
const powers = (G: GameState, player: Player, plant: number) =>
    offered(G, player).find((m) => m.powerPlant == plant)!.citiesPowered;

describe('SwitzerlandCustom', () => {
    it('is never dealt by Random', () => {
        for (let s = 0; s < 300; s++) {
            for (const variant of ['original', 'recharged'] as const) {
                expect(setup(3, { map: 'Random', variant }, 'r' + s).map.name).to.not.equal('SwitzerlandCustom');
            }
        }
    });

    it('has 49 cities, 7 per region, every city linked, no duplicate links', () => {
        const byRegion = new Map<string, number>();
        switzerland.cities.forEach((c) => byRegion.set(c.region, (byRegion.get(c.region) ?? 0) + 1));
        expect(switzerland.cities.length).to.equal(49);
        expect([...byRegion.values()]).to.deep.equal([7, 7, 7, 7, 7, 7, 7]);
        const names = new Set(switzerland.cities.map((c) => c.name));
        const seen = new Set<string>();
        const degree = new Map<string, number>();
        for (const l of switzerland.connections) {
            l.nodes.forEach((n) => expect(names.has(n), n).to.equal(true));
            const k = [...l.nodes].sort().join('|');
            expect(seen.has(k), k).to.equal(false);
            seen.add(k);
            l.nodes.forEach((n) => degree.set(n, (degree.get(n) ?? 0) + 1));
        }
        for (const n of names) expect(degree.get(n) ?? 0, n).to.be.at.least(2);
    });

    it('deals every player count a playable board', () => {
        for (let players = 2; players <= 6; players++) {
            for (let s = 0; s < 50; s++) {
                const G = setup(players, { map: 'SwitzerlandCustom', variant: 'original' }, 'p' + s);
                expect(G.map.name).to.equal('SwitzerlandCustom');
                expect(G.map.cities.length).to.be.greaterThan(0);
            }
        }
    });

    it('is an expensive country: coal from $3, oil from $4, cheese from $6, uranium as usual', () => {
        for (const variant of ['original', 'recharged'] as const) {
            const G = setup(4, { map: 'SwitzerlandCustom', variant }, 'prices');
            expect([G.coalMarket, G.oilMarket, G.garbageMarket, G.uraniumMarket], variant).to.deep.equal([
                18, 15, 9, 2,
            ]);
        }
    });

    it("opens all three of Geneva's spaces from Step 1, and only Geneva's", () => {
        for (const c of switzerland.cities) {
            expect(c.stepSlots, c.name).to.deep.equal(c.name == 'Geneva' ? [3, 3, 3] : undefined);
        }
    });

    it('marks the seven Alpine cities', () => {
        expect(
            switzerland.cities
                .filter((c) => c.alpine)
                .map((c) => c.name)
                .sort()
        ).to.deep.equal(['Airolo', 'Andermatt', 'Davos', 'Engelberg', 'Grindelwald', 'St. Moritz', 'Zermatt'].sort());
    });

    describe('Alpine hydro: +1 per ecological plant, capped by Alpine cities owned', () => {
        it('gives nothing without an Alpine city', () => {
            const { G, player } = bureaucracy([wind(13, 1)], ['Bern', 'Thun']);
            expect(powers(G, player, 13)).to.equal(1);
            expect(calculateMaxCitiesPowered(G, player)).to.equal(1);
        });

        it('gives one ecological plant +1 with one Alpine city, and not the second', () => {
            const { G, player } = bureaucracy([wind(13, 1), wind(18, 2)], ['Zermatt', 'Bern', 'Thun', 'Sion', 'Biel']);
            expect(alpineBonusLeft(G, player)).to.equal(1);
            expect(powers(G, player, 13)).to.equal(2);
            expect(powers(G, player, 18)).to.equal(3);
            // fire 18 with the bonus: the bonus is spent, 13 is back to its printed value
            player.powerPlantsNotUsed = [13];
            expect(alpineBonusLeft(G, player)).to.equal(0);
            expect(powers(G, player, 13)).to.equal(1);
            // best case across both: 1 + 2 + one bonus
            player.powerPlantsNotUsed = [13, 18];
            expect(calculateMaxCitiesPowered(G, player)).to.equal(4);
        });

        it('gives both ecological plants +1 with two Alpine cities', () => {
            const { G, player } = bureaucracy(
                [wind(13, 1), wind(18, 2)],
                ['Zermatt', 'Davos', 'Bern', 'Thun', 'Sion', 'Biel']
            );
            expect(calculateMaxCitiesPowered(G, player)).to.equal(5);
            player.powerPlantsNotUsed = [13];
            expect(powers(G, player, 13)).to.equal(2);
        });

        it('never boosts fuelled plants, and never powers more cities than owned', () => {
            const { G, player } = bureaucracy([coal(10, 2), wind(13, 1)], ['Zermatt', 'Bern'], 2);
            expect(powers(G, player, 10)).to.equal(2);
            expect(powers(G, player, 13)).to.equal(2);
            expect(calculateMaxCitiesPowered(G, player)).to.equal(2);
        });

        it('never boosts the fusion plant (John, 2026-11-19: 6 + 1 = 7 from one card is too strong)', () => {
            const fusion: PowerPlant = { number: 50, type: PowerPlantType.Nuclear, cost: 0, citiesPowered: 6 };
            const cities = ['Zermatt', 'Bern', 'Thun', 'Sion', 'Biel', 'Lausanne', 'Nyon', 'Montreux'];
            const { G, player } = bureaucracy([fusion, wind(13, 1)], cities);
            expect(powers(G, player, 50)).to.equal(6);
            // the one Alpine +1 goes to the green plant: 6 + (1 + 1)
            expect(calculateMaxCitiesPowered(G, player)).to.equal(8);
            player.powerPlantsNotUsed = [50];
            expect(powers(G, player, 50)).to.equal(6);
        });

        it('leaves every other map untouched', () => {
            const { G, player } = bureaucracy([wind(13, 1)], ['Zermatt']);
            G.map = setup(3, { map: 'Germany', variant: 'original' }, 'g').map;
            expect(alpineBonusLeft(G, player)).to.equal(0);
            expect(powers(G, player, 13)).to.equal(1);
        });
    });
});
