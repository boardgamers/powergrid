import { expect } from 'chai';
import { agedCheese, alpineBonusLeft, availableMoves, cheeseMix, ripenCheese } from './available-moves';
import { calculateMaxCitiesPowered, move, moveAI, setup } from './engine';
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

describe('SwitzerlandCustom cheese cellar', () => {
    const cheese = (number: number, cost: number, citiesPowered: number): PowerPlant => ({
        number,
        type: PowerPlantType.Garbage,
        cost,
        citiesPowered,
    });
    const cityNames = (n: number) =>
        switzerland.cities
            .filter((c) => !c.alpine)
            .slice(0, n)
            .map((c) => c.name);

    it('picks the thriftiest mix: least waste, then fewest cubes', () => {
        expect(cheeseMix(3, 5, 0)).to.deep.equal({ aged: 0, fresh: 3 });
        expect(cheeseMix(3, 5, 2)).to.deep.equal({ aged: 1, fresh: 1 }); // plant 30: one aged + one fresh
        expect(cheeseMix(2, 0, 1)).to.deep.equal({ aged: 1, fresh: 0 }); // plant 19 on one aged cube
        expect(cheeseMix(3, 0, 2)).to.deep.equal({ aged: 2, fresh: 0 }); // overshoot is wasted, but it runs
        expect(cheeseMix(3, 0, 1)).to.equal(undefined);
        expect(cheeseMix(1, 1, 1)).to.deep.equal({ aged: 0, fresh: 1 }); // never burn an aged cube for one
    });

    it('ripens fresh cheese only in a plant that rested, and an aged cube burns as two', () => {
        const { G, player } = bureaucracy([cheese(19, 2, 3)], cityNames(3));
        player.garbageLeft = 2;
        // plant 19 rests this round: both cubes age
        expect(ripenCheese(G, player)).to.equal(2);
        expect(agedCheese(player)).to.equal(2);
        // next round: one aged cube is a full run, twice over
        player.powerPlantsNotUsed = [19];
        const move = offered(G, player).find((m) => m.powerPlant == 19) as any;
        expect(move.agedSpent).to.equal(1);
        expect(move.resourcesSpent.length).to.equal(1);
        expect(calculateMaxCitiesPowered(G, player)).to.equal(3);
    });

    it('does not ripen cheese in a plant that fired, and aged cheese never ages again', () => {
        const { G, player } = bureaucracy([cheese(19, 2, 3)], cityNames(3));
        player.garbageLeft = 4;
        player.powerPlantsNotUsed = []; // 19 fired
        expect(ripenCheese(G, player)).to.equal(0);
        player.powerPlantsNotUsed = [19];
        player.agedCheese = 4;
        expect(ripenCheese(G, player)).to.equal(0);
        expect(agedCheese(player)).to.equal(4);
    });

    it('a resting plant ripens only the room it has left', () => {
        // 19 (holds 4) fired, 24 (holds 4) rested; 6 cubes held, 4 already aged
        const { G, player } = bureaucracy([cheese(19, 2, 3), cheese(24, 2, 4)], cityNames(5));
        player.garbageLeft = 6;
        player.agedCheese = 4;
        player.powerPlantsNotUsed = [24];
        // the 4 aged fill 19's room first, so 24 has all 4 of its room: the 2 fresh ripen
        expect(ripenCheese(G, player)).to.equal(2);
        expect(agedCheese(player)).to.equal(6);
    });

    it('spends aged cheese when the plant fires, through the real move', () => {
        const G = setup(3, { map: 'SwitzerlandCustom', variant: 'original' }, 'cellar-move');
        // Play to the first Bureaucracy, then hand the current player a cheese plant with aged cheese.
        let state = G;
        for (let i = 0; i < 400 && state.phase != Phase.Bureaucracy; i++)
            state = moveAI(state, state.currentPlayers[0]);
        expect(state.phase).to.equal(Phase.Bureaucracy);
        const p = state.players[state.currentPlayers[0]];
        p.powerPlants = [cheese(19, 2, 3)];
        p.powerPlantsNotUsed = [19];
        p.garbageLeft = 3;
        p.agedCheese = 2;
        p.cities = cityNames(3).map((name) => ({ name, position: 0 }));
        p.availableMoves = availableMoves(state, p);
        const use = (p.availableMoves[MoveName.UsePowerPlant] as any[]).find((m) => m.powerPlant == 19);
        state = move(state, { name: MoveName.UsePowerPlant, data: use }, state.currentPlayers[0]);
        const after = state.players[state.players.indexOf(state.players.find((x) => x.id == p.id)!)];
        expect(after.garbageLeft).to.equal(2);
        expect(agedCheese(after)).to.equal(1);
    });

    it('keeps the other aged cube aged after burning one (John, 2026-11-19: plant 6, two aged, used one)', () => {
        const G = setup(3, { map: 'SwitzerlandCustom', variant: 'original' }, 'cellar-six');
        let state = G;
        for (let i = 0; i < 400 && state.phase != Phase.Bureaucracy; i++)
            state = moveAI(state, state.currentPlayers[0]);
        const p = state.players[state.currentPlayers[0]];
        p.powerPlants = [cheese(6, 1, 1)];
        p.powerPlantsNotUsed = [6];
        p.garbageLeft = 2;
        p.agedCheese = 2;
        p.cities = cityNames(1).map((name) => ({ name, position: 0 }));
        p.availableMoves = availableMoves(state, p);
        const use = (p.availableMoves[MoveName.UsePowerPlant] as any[]).find((m) => m.powerPlant == 6);
        expect(use.agedSpent).to.equal(1);
        state = move(state, { name: MoveName.UsePowerPlant, data: use }, state.currentPlayers[0]);
        const after = state.players.find((x) => x.id == p.id)!;
        expect(after.garbageLeft).to.equal(1);
        expect(agedCheese(after)).to.equal(1);
    });

    it('leaves garbage alone on every other map', () => {
        const { G, player } = bureaucracy([cheese(19, 2, 3)], ['Bern']);
        G.map = setup(3, { map: 'Germany', variant: 'original' }, 'g').map;
        player.garbageLeft = 2;
        expect(ripenCheese(G, player)).to.equal(0);
        const m = offered(G, player).find((x) => x.powerPlant == 19) as any;
        expect(m.agedSpent).to.equal(undefined);
        expect(m.resourcesSpent.length).to.equal(2);
    });
});
