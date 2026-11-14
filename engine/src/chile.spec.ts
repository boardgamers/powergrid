import { expect } from 'chai';
import { cloneDeep } from 'lodash';
import 'mocha';
import seedrandom from 'seedrandom';
import { createAnalysisScenario } from './analysis';
import { availableMoves, computeRegionGraph, marketSideOf } from './available-moves';
import { applyChileStep3, currentPlayers, ended, move, reconstructState, setup, stripSecret } from './engine';
import { GameState, Phase, PowerPlant, PowerPlantType, ResourceType } from './gamestate';
import { map as chile } from './maps/chile';
import { Move, MoveName } from './move';
import { powerPlants } from './powerPlants';
import prices from './prices';

const URANIUM = [11, 17, 23, 28, 34, 39];
const SET_ASIDE = [33, 37, 44];
const NORTH = ['brown', 'yellow'];

/** Plays seeded legal-random moves (never ReopenPowering) until `stop` holds or the game ends. */
function playUntil(G: GameState, seed: string, stop: (G: GameState) => boolean = () => false, maxMoves = 20000) {
    const rng = seedrandom(seed);
    for (let i = 0; i < maxMoves && !ended(G) && !stop(G); i++) {
        const player = Math.min(...currentPlayers(G));
        const available = G.players[player].availableMoves as Record<string, unknown[] | undefined>;
        const names = Object.keys(available).filter((n) => n != MoveName.ReopenPowering && available[n]?.length);
        const name = names[Math.floor(rng() * names.length)];
        const options = available[name]!;
        move(G, { name, data: options[Math.floor(rng() * options.length)] } as Move, player);
    }
    return G;
}

const allPlants = (G: GameState) => [
    ...G.powerPlantsDeck,
    ...G.actualMarket,
    ...G.futureMarket,
    ...([] as PowerPlant[]).concat(...G.players.map((p) => p.powerPlants)),
];

/** A fresh 4P game at the start of the Resources phase, with `cities` given to player 0. */
function resourcesState(cities: string[], variant: 'original' | 'recharged' = 'original') {
    const G = setup(4, { map: 'Chile', variant }, 'chile-resources');
    G.phase = Phase.Resources;
    const player = G.players[0];
    player.cities = cities.map((name) => ({ name, position: 0 }));
    player.powerPlants = [
        cloneDeep(powerPlants.find((pp) => pp.number == 4)!),
        cloneDeep(powerPlants.find((pp) => pp.number == 7)!),
    ];
    player.coalCapacity = 4;
    player.oilCapacity = 6;
    player.money = 100;
    G.currentPlayers = [0];
    player.availableMoves = availableMoves(G, player);
    return G;
}

const buyOptions = (G: GameState, p = 0) =>
    (G.players[p].availableMoves?.[MoveName.BuyResource] ?? []) as { resource: ResourceType; side?: string }[];

describe('Chile', () => {
    describe('board', () => {
        it('has six regions of seven cities, Salta in no region, a grid for every city, 58 connections and two gates', () => {
            const byRegion: Record<string, number> = {};
            for (const c of chile.cities) byRegion[c.region] = (byRegion[c.region] ?? 0) + 1;
            expect(byRegion).to.deep.equal({ brown: 7, yellow: 7, purple: 7, red: 7, green: 7, pink: 7, '': 1 });
            const salta = chile.cities.find((c) => c.name == 'Salta')!;
            expect(salta.region).to.equal('');
            expect(salta.grid).to.equal('North');
            expect(salta.singleOccupancy).to.be.true;
            expect(chile.cities.every((c) => c.grid == 'North' || c.grid == 'Central')).to.be.true;
            // Brown and yellow each hold five North and two Central cities; the other regions are all Central.
            for (const region of NORTH) {
                const inRegion = chile.cities.filter((c) => c.region == region);
                expect(
                    inRegion.filter((c) => c.grid == 'North'),
                    region
                ).to.have.length(5);
                expect(
                    inRegion.filter((c) => c.grid == 'Central'),
                    region
                ).to.have.length(2);
            }
            expect(chile.cities.filter((c) => c.region && !NORTH.includes(c.region)).every((c) => c.grid == 'Central'))
                .to.be.true;
            expect(chile.connections).to.have.length(58);
            expect(chile.step3Connections).to.have.length(2);
        });

        it('joins the grids only by the gates, one inside each northern region', () => {
            const city = (name: string) => chile.cities.find((c) => c.name == name)!;
            for (const con of chile.connections) {
                const [a, b] = con.nodes.map(city);
                expect(a.grid, con.nodes.join('-')).to.equal(b.grid);
            }
            const gateRegions = chile.step3Connections!.map((gate) => {
                const [a, b] = gate.nodes.map(city);
                expect([a.grid, b.grid].sort(), gate.nodes.join('-')).to.deep.equal(['Central', 'North']);
                expect(a.region, gate.nodes.join('-')).to.equal(b.region);
                return a.region;
            });
            expect(gateRegions.sort()).to.deep.equal(['brown', 'yellow']);
            // Every city keeps a connection.
            const all = [...chile.connections, ...chile.step3Connections!];
            for (const c of chile.cities)
                expect(
                    all.some((con) => con.nodes.includes(c.name)),
                    c.name
                ).to.be.true;
        });

        it('builds the region graph from open connections; Salta is not a play area', () => {
            const graph = computeRegionGraph(chile);
            expect([...graph.regions].sort()).to.deep.equal(['brown', 'green', 'pink', 'purple', 'red', 'yellow']);
            const adjacent = (r: string) => graph.regionConnections[graph.regions.indexOf(r)];
            expect(adjacent('purple')).to.include.members(['brown', 'yellow', 'red']);
            expect(adjacent('red')).to.include.members(['purple', 'green', 'pink']);
        });

        it('always plays brown and yellow, with fixed areas at 2-4P and green or pink added at 5-6P', () => {
            const fixed: Record<number, string[]> = {
                2: ['brown', 'purple', 'yellow'],
                3: ['brown', 'purple', 'yellow'],
                4: ['brown', 'purple', 'red', 'yellow'],
            };
            const seen: Record<number, Set<string>> = {};
            for (const n of [2, 3, 4, 5, 6]) {
                seen[n] = new Set();
                for (let i = 0; i < 60; i++) {
                    const G = setup(n, { map: 'Chile' }, `areas-${n}-${i}`);
                    const regions = [...new Set(G.map.cities.map((c) => c.region).filter((r) => r))].sort();
                    expect(regions, `${n}P`).to.include.members(NORTH);
                    if (fixed[n]) expect(regions, `${n}P`).to.deep.equal(fixed[n]);
                    else expect(regions, `${n}P`).to.have.length(5);
                    expect(G.map.cities.some((c) => c.name == 'Salta')).to.be.true;
                    expect(G.map.step3Connections).to.have.length(2);
                    expect(
                        G.map.connections.every((con) =>
                            con.nodes.every((nm) => G.map.cities.some((c) => c.name == nm))
                        )
                    ).to.be.true;
                    seen[n].add(regions.join(','));
                }
            }
            for (const n of [5, 6]) {
                expect([...seen[n]].sort(), `${n}P`).to.deep.equal([
                    'brown,green,purple,red,yellow',
                    'brown,pink,purple,red,yellow',
                ]);
            }
        });

        it('drafts only the remaining regions when players choose them', () => {
            for (const n of [3, 5]) {
                const G = setup(n, { map: 'Chile', chooseRegions: true }, `draft-${n}`);
                expect(G.phase).to.equal(Phase.RegionSelection);
                expect(G.regionDraft!.picked).to.deep.equal(NORTH);
                const first = Math.min(...currentPlayers(G));
                expect(G.players[first].availableMoves![MoveName.ChooseRegion]).to.deep.equal(['purple']);
                playUntil(G, `draft-${n}`, (s) => s.phase != Phase.RegionSelection);
                const regions = [...new Set(G.map.cities.map((c) => c.region).filter((r) => r))].sort();
                expect(regions).to.include.members([...NORTH, 'purple']);
                expect(regions).to.have.length(n == 3 ? 3 : 5);
            }
        });
    });

    describe('setup', () => {
        for (const variant of ['original', 'recharged'] as const) {
            for (const n of [2, 3, 4, 5, 6]) {
                it(`${variant} ${n}P: no uranium, plants 33/37/44 set aside, none removed for the player count`, () => {
                    const G = setup(n, { map: 'Chile', variant }, `deck-${variant}-${n}`);
                    const inGame = [...G.powerPlantsDeck, ...G.actualMarket, ...G.futureMarket].map((pp) => pp.number);
                    const expected = powerPlants
                        .map((pp) => pp.number)
                        .filter((x) => !URANIUM.includes(x) && !SET_ASIDE.includes(x));
                    expect([...inGame].sort((a, b) => a - b)).to.deep.equal([...expected].sort((a, b) => a - b));
                    expect(G.setAsidePlants!.map((pp) => pp.number)).to.deep.equal(SET_ASIDE);
                    expect(G.powerPlantsDeck[G.powerPlantsDeck.length - 1].type).to.equal(PowerPlantType.Step3);
                    if (variant == 'original') {
                        expect(G.actualMarket.map((pp) => pp.number)).to.deep.equal([3, 4, 5, 6]);
                        expect(G.futureMarket.map((pp) => pp.number)).to.deep.equal([7, 8, 9, 10]);
                        expect(G.powerPlantsDeck[0].number).to.equal(13);
                    } else {
                        expect(
                            [...G.actualMarket, ...G.futureMarket, G.powerPlantsDeck[0]].every((pp) => pp.number <= 15)
                        ).to.be.true;
                    }
                });
            }
        }

        it('starts the markets as in the rules, from one shared supply, with no uranium', () => {
            for (const variant of ['original', 'recharged'] as const) {
                const G = setup(4, { map: 'Chile', variant }, 'markets');
                expect([G.coalMarketNorth, G.oilMarketNorth, G.garbageMarketNorth]).to.deep.equal([12, 8, 0]);
                expect([G.coalMarket, G.oilMarket, G.garbageMarket, G.uraniumMarket]).to.deep.equal([12, 10, 4, 0]);
                expect([G.coalSupply, G.oilSupply, G.garbageSupply, G.uraniumSupply]).to.deep.equal([0, 6, 20, 0]);
                // The markets fill from the expensive end: North coal from $1 with two per space, Central coal from $1
                // with one per space, Central oil from $4, garbage from $7, North oil from $1.
                expect(G.coalPricesNorth![G.coalPricesNorth!.length - 12]).to.equal(1);
                expect(G.coalPrices![G.coalPrices!.length - 12]).to.equal(1);
                expect(G.oilPrices![G.oilPrices!.length - 10]).to.equal(4);
                expect(G.garbagePrices![G.garbagePrices!.length - 4]).to.equal(7);
                expect(G.oilPricesNorth![G.oilPricesNorth!.length - 8]).to.equal(1);
                expect(G.garbagePricesNorth).to.deep.equal([]);
            }
        });

        it('builds for the standard deck only, and stays out of the random map pick', () => {
            expect(() => setup(4, { map: 'Chile', variant: 'recharged', plantDeck: 'set1' }, 'x')).to.throw(/standard/);
            expect(() => setup(4, { map: 'Chile', randomizeMap: true }, 'x')).to.throw(/randomized/);
            for (let i = 0; i < 200; i++) {
                expect(setup(4, { map: 'Random' }, `random-${i}`).map.name).to.not.equal('Chile');
            }
        });
    });

    describe('buying resources', () => {
        it('lets a player with no cities choose one market for the turn', () => {
            const G = resourcesState([]);
            const options = buyOptions(G);
            expect(options.some((o) => o.side == 'north')).to.be.true;
            expect(options.some((o) => o.side == 'south')).to.be.true;
            move(G, { name: MoveName.BuyResource, data: { resource: ResourceType.Coal, side: 'north' } } as Move, 0);
            expect(G.chosenSide).to.equal('north');
            expect(buyOptions(G).every((o) => o.side == 'north')).to.be.true;
            move(G, { name: MoveName.Pass, data: true } as Move, 0);
            expect(G.chosenSide).to.be.undefined;
        });

        it('lets a player with cities buy only from their grid’s market', () => {
            const north = resourcesState(['Calama']);
            expect(marketSideOf(north, north.players[0])).to.equal('north');
            expect(buyOptions(north)).to.not.be.empty;
            expect(buyOptions(north).every((o) => o.side == 'north')).to.be.true;
            expect(() =>
                move(
                    north,
                    { name: MoveName.BuyResource, data: { resource: ResourceType.Coal, side: 'south' } } as Move,
                    0
                )
            ).to.throw();

            const central = resourcesState(['Santiago N', 'Santiago E']);
            expect(marketSideOf(central, central.players[0])).to.equal('south');
            expect(buyOptions(central).every((o) => o.side == 'south')).to.be.true;
        });

        it('goes by the city’s grid, not its region: Taltal and Copiapó buy from Central, Antofagasta and Calama from North', () => {
            for (const [city, side] of [
                ['Taltal', 'south'],
                ['Chañaral', 'south'],
                ['El Salvador', 'south'],
                ['Copiapó', 'south'],
                ['Antofagasta', 'north'],
                ['Calama', 'north'],
            ]) {
                const G = resourcesState([city]);
                expect(marketSideOf(G, G.players[0]), city).to.equal(side);
                expect(buyOptions(G), city).to.not.be.empty;
                expect(
                    buyOptions(G).every((o) => o.side == side),
                    city
                ).to.be.true;
            }
        });

        it('never offers garbage or uranium in the North', () => {
            const G = resourcesState(['Calama']);
            G.players[0].powerPlants.push(cloneDeep(powerPlants.find((pp) => pp.number == 6)!));
            G.players[0].garbageCapacity = 2;
            G.players[0].availableMoves = availableMoves(G, G.players[0]);
            expect(buyOptions(G).map((o) => o.resource)).to.not.include(ResourceType.Garbage);
            expect(buyOptions(G).map((o) => o.resource)).to.not.include(ResourceType.Uranium);
        });
    });

    describe('building', () => {
        function buildState(cities: string[], step = 1) {
            const G = setup(6, { map: 'Chile' }, 'chile-build');
            // Put every region in play.
            G.map = cloneDeep({ ...chile, step3Connections: chile.step3Connections });
            G.phase = Phase.Building;
            G.step = step;
            const player = G.players[0];
            player.cities = cities.map((name) => ({ name, position: 0 }));
            player.money = 500;
            G.currentPlayers = [0];
            player.availableMoves = availableMoves(G, player);
            return G;
        }
        const builds = (G: GameState) =>
            (G.players[0].availableMoves?.[MoveName.Build] ?? []) as { name: string; price: number }[];

        it('offers no build across a gate before Step 3, and the gates’ cost once they open', () => {
            const gridOf = (name: string) => chile.cities.find((c) => c.name == name)!.grid;
            for (const step of [1, 2]) {
                for (const [start, grid] of [
                    ['Antofagasta', 'North'],
                    ['Taltal', 'Central'],
                ]) {
                    const G = buildState([start], step);
                    expect(builds(G), start).to.not.be.empty;
                    expect(
                        builds(G).every((b) => gridOf(b.name) == grid),
                        `${start} step ${step}`
                    ).to.be.true;
                }
            }
            const G = buildState(['Antofagasta'], 3);
            applyChileStep3(G);
            G.players[0].availableMoves = availableMoves(G, G.players[0]);
            expect(builds(G).find((b) => b.name == 'Taltal')!.price).to.equal(13 + 10);
            const sierra = buildState(['Sierra Gorda'], 3);
            applyChileStep3(sierra);
            sierra.players[0].availableMoves = availableMoves(sierra, sierra.players[0]);
            expect(builds(sierra).find((b) => b.name == 'El Salvador')!.price).to.equal(20 + 10);
        });

        it('keeps Salta to one city, never a first city, reached for its connection cost only', () => {
            const first = buildState([]);
            expect(builds(first).map((b) => b.name)).to.not.include('Salta');
            expect(builds(first).map((b) => b.name)).to.include('San Pedro');
            const G = buildState(['San Pedro']);
            expect(builds(G).find((b) => b.name == 'Salta')!.price).to.equal(20);
            G.players[1].cities = [{ name: 'Salta', position: 0 }];
            G.step = 3;
            G.players[0].availableMoves = availableMoves(G, G.players[0]);
            expect(builds(G).map((b) => b.name)).to.not.include('Salta');
        });

        it('joins the Santiago ring at cost 0', () => {
            const G = buildState(['Santiago N']);
            for (const name of ['Santiago E', 'Santiago S', 'Santiago W'])
                expect(builds(G).find((b) => b.name == name)!.price).to.equal(10);
        });
    });

    describe('bureaucracy', () => {
        /** Plays to the last Bureaucracy move of round 1, sets the markets and supply, then plays that move. */
        function restock(n: number, set: (G: GameState) => void) {
            const G = setup(n, { map: 'Chile' }, `restock-${n}`);
            playUntil(
                G,
                'restock',
                (s) => s.phase == Phase.Bureaucracy && s.players.filter((p) => !p.passed).length == 1
            );
            expect(G.phase).to.equal(Phase.Bureaucracy);
            const last = G.players.findIndex((p) => !p.passed);
            const player = G.players[last];
            player.coalLeft = player.oilLeft = player.garbageLeft = 0;
            player.availableMoves = availableMoves(G, player);
            set(G);
            move(G, { name: MoveName.Pass, data: true } as Move, last);
            expect(G.round).to.equal(2);
            return G;
        }
        const empty = (G: GameState) => {
            G.coalMarketNorth = G.oilMarketNorth = 0;
            G.coalMarket = G.oilMarket = G.garbageMarket = 0;
        };

        it('restocks North then Central from the table, garbage only in Central', () => {
            const table: Record<number, number[]> = {
                // north coal, north oil, central coal, central oil, central garbage (Step 1)
                3: [2, 1, 2, 1, 1],
                4: [2, 1, 3, 2, 2],
                5: [2, 2, 3, 2, 3],
                6: [3, 2, 4, 3, 3],
            };
            for (const n of [3, 4, 5, 6]) {
                const G = restock(n, (s) => {
                    empty(s);
                    s.coalSupply = s.oilSupply = s.garbageSupply = 20;
                });
                expect(
                    [G.coalMarketNorth, G.oilMarketNorth, G.coalMarket, G.oilMarket, G.garbageMarket],
                    `${n}P`
                ).to.deep.equal(table[n]);
                expect(G.garbageMarketNorth).to.equal(0);
                expect(G.uraniumMarket).to.equal(0);
            }
        });

        it('gives the North first call on a short supply', () => {
            const G = restock(4, (s) => {
                empty(s);
                s.coalSupply = 3;
                s.oilSupply = 1;
            });
            expect([G.coalMarketNorth, G.coalMarket]).to.deep.equal([2, 1]);
            expect([G.oilMarketNorth, G.oilMarket]).to.deep.equal([1, 0]);
        });

        it('restocks only one oil per market in Step 2', () => {
            const G = restock(6, (s) => {
                empty(s);
                s.step = 2;
                s.coalSupply = s.oilSupply = s.garbageSupply = 20;
            });
            expect([G.coalMarketNorth, G.oilMarketNorth, G.coalMarket, G.oilMarket, G.garbageMarket]).to.deep.equal([
                4, 1, 6, 1, 5,
            ]);
        });
    });

    describe('Step 3', () => {
        let boostedUses = 0;
        it('merges the markets, opens the gates, puts 33/37/44 on top and boosts every ecological plant by one', () => {
            const catalogue = cloneDeep(powerPlants);
            const G = setup(6, { map: 'Chile' }, 'step3-unit');
            G.map = cloneDeep(chile);
            G.coalMarketNorth = 5;
            G.oilMarketNorth = 3;
            G.coalMarket = 9;
            G.oilMarket = 7;
            G.garbageMarket = 6;
            const wind13 = G.powerPlantsDeck.find((pp) => pp.number == 13)!;
            G.players[0].powerPlants = [wind13, cloneDeep(powerPlants.find((pp) => pp.number == 50)!)];
            G.powerPlantsDeck = G.powerPlantsDeck.filter((pp) => pp.number != 13);
            G.step = 3;
            const deckBefore = G.powerPlantsDeck.map((pp) => pp.number);

            applyChileStep3(G);

            // 1. One market on the standard tracks, holding everything from both.
            expect([G.coalMarket, G.oilMarket, G.garbageMarket]).to.deep.equal([14, 10, 6]);
            expect(G.coalPrices).to.deep.equal(prices[ResourceType.Coal]);
            expect(G.oilPrices).to.deep.equal(prices[ResourceType.Oil]);
            expect(G.garbagePrices).to.deep.equal(prices[ResourceType.Garbage]);
            expect(G.coalPrices![24 - 14]).to.equal(4); // filled from the most expensive space down
            expect(G.coalMarketNorth).to.be.undefined;
            expect(G.coalResupplyNorth).to.be.undefined;
            // 2. Gates open.
            expect(G.map.connections).to.have.length(60);
            expect(G.map.step3Connections).to.be.undefined;
            // 3. Set-aside plants on top, in order.
            expect(G.powerPlantsDeck.map((pp) => pp.number)).to.deep.equal([...SET_ASIDE, ...deckBefore]);
            expect(G.setAsidePlants).to.be.undefined;
            // 4. Ecological plants +1 everywhere; fusion and fuelled plants unchanged; the catalogue untouched.
            const printed = (num: number) => catalogue.find((pp) => pp.number == num)!.citiesPowered;
            for (const pp of allPlants(G)) {
                expect(pp.citiesPowered, `plant ${pp.number}`).to.equal(
                    printed(pp.number) + (pp.type == PowerPlantType.Wind ? 1 : 0)
                );
            }
            expect(G.players[0].powerPlants.map((pp) => pp.citiesPowered)).to.deep.equal([2, 6]);
            expect(powerPlants).to.deep.equal(catalogue);

            // Once only.
            const after = cloneDeep(G);
            applyChileStep3(G);
            expect(G).to.deep.equal(after);
        });

        for (const variant of ['original', 'recharged'] as const) {
            for (const n of [3, 4, 5, 6]) {
                it(`${variant} ${n}P: happens in play, and the boosted plants power one more city`, () => {
                    const G = setup(n, { map: 'Chile', variant }, `step3-${variant}-${n}`);
                    const catalogue = cloneDeep(powerPlants);
                    let before: GameState | undefined;
                    playUntil(G, `play-${variant}-${n}`, (s) => {
                        if (s.step < 3) before = cloneDeep(s);
                        return s.step == 3;
                    });
                    expect(G.step).to.equal(3);
                    const events = G.log.filter((l) => l.type == 'event').map((l) => (l as { event: string }).event);
                    expect(events).to.include('Step 3: the North and Central resource markets merge into one.');
                    expect(G.coalMarketNorth).to.be.undefined;
                    // Resources are conserved through the merge (the move that started Step 3 may also restock).
                    const total = (s: GameState, r: 'coal' | 'oil' | 'garbage') =>
                        (s as any)[`${r}Market`] +
                        ((s as any)[`${r}MarketNorth`] ?? 0) +
                        (s as any)[`${r}Supply`] +
                        s.players.reduce((a, p) => a + (p as any)[`${r}Left`], 0);
                    for (const r of ['coal', 'oil', 'garbage'] as const)
                        expect(total(G, r), r).to.equal(total(before!, r));
                    for (const pp of allPlants(G)) {
                        const printed = catalogue.find((c) => c.number == pp.number)!.citiesPowered;
                        expect(pp.citiesPowered).to.equal(printed + (pp.type == PowerPlantType.Wind ? 1 : 0));
                    }
                    // The set-aside plants are next out of the deck (unless already drawn into the market).
                    const next = G.powerPlantsDeck.slice(0, 3).map((pp) => pp.number);
                    const drawn = [
                        ...G.actualMarket,
                        ...G.futureMarket,
                        ...([] as PowerPlant[]).concat(...G.players.map((p) => p.powerPlants)),
                    ].map((pp) => pp.number);
                    expect(SET_ASIDE.every((x) => next.includes(x) || drawn.includes(x))).to.be.true;

                    // Play on: an ecological plant in a hand is offered for its boosted number of cities.
                    playUntil(G, `rest-${variant}-${n}`, (s) => {
                        if (s.phase != Phase.Bureaucracy) return false;
                        return s.players.some((p) =>
                            (p.availableMoves?.[MoveName.UsePowerPlant] ?? []).some(
                                (u) =>
                                    p.powerPlants.find((pp) => pp.number == u.powerPlant)?.type == PowerPlantType.Wind
                            )
                        );
                    });
                    if (!ended(G)) {
                        boostedUses++;
                        const p = G.players.find((pl) =>
                            (pl.availableMoves?.[MoveName.UsePowerPlant] ?? []).some(
                                (u) =>
                                    pl.powerPlants.find((pp) => pp.number == u.powerPlant)?.type == PowerPlantType.Wind
                            )
                        )!;
                        const use = p.availableMoves![MoveName.UsePowerPlant]!.find(
                            (u) => p.powerPlants.find((pp) => pp.number == u.powerPlant)?.type == PowerPlantType.Wind
                        )!;
                        expect(use.citiesPowered).to.equal(
                            catalogue.find((c) => c.number == use.powerPlant)!.citiesPowered + 1
                        );
                    }
                });
            }
        }

        it('saw a boosted ecological plant offered in Bureaucracy in most of those games', () => {
            expect(boostedUses).to.be.at.least(4);
        });
    });

    describe('hidden-deck replay and analysis', () => {
        const isGate = (con: { nodes: string[] }) =>
            chile.step3Connections!.some((gate) => gate.nodes.every((n) => con.nodes.includes(n)));
        const toStep3 = (seed: string, variant: 'original' | 'recharged' = 'original') =>
            playUntil(setup(4, { map: 'Chile', variant }, seed), seed, (s) => s.step == 3 && s.phase == Phase.Building);

        it('rewinds a secret-seed game to closed gates, and replays its Step 3 events', () => {
            // The full log isn't compared: on every map, a hidden-deck replay can leave out a "drawn from the deck"
            // entry around the Step 3 card (USA seed r2 too), which predates Chile.
            const step3Events = (s: GameState) =>
                s.log.map((l) => (l as { event?: string }).event ?? '').filter((e) => e.startsWith('Step 3:'));
            for (const seed of ['r1', 'r2', 'r3', 'r4', 'r5', 'r6']) {
                const G = toStep3(seed);
                expect(G.step, seed).to.equal(3);
                const s = stripSecret(cloneDeep(G), 0);
                const early = reconstructState(s, 30);
                expect(early.step).to.be.below(3);
                expect(early.map.connections.filter(isGate), seed).to.be.empty;
                expect(early.map.step3Connections, seed).to.have.length(2);
                const full = reconstructState(s, s.log.length);
                expect(step3Events(full), seed).to.deep.equal(step3Events(G));
                expect(step3Events(G), seed).to.have.length(4);
                expect(full.map.connections.filter(isGate)).to.have.length(2);
                expect(full.players.map((p) => [p.money, p.cities.length])).to.deep.equal(
                    G.players.map((p) => [p.money, p.cities.length])
                );
            }
        });

        for (const variant of ['original', 'recharged'] as const) {
            it(`${variant}: analysis scenarios deal a Chile deck in every step`, () => {
                for (const [label, stop] of [
                    ['step 1', (s: GameState) => s.round == 3],
                    ['step 2', (s: GameState) => s.step == 2],
                    ['step 3', (s: GameState) => s.step == 3],
                ] as const) {
                    const G = playUntil(setup(4, { map: 'Chile', variant }, 'scenario'), 'scenario', stop);
                    const s = createAnalysisScenario(G, { player: 0, seed: 'x' });
                    const deck = s.powerPlantsDeck.map((pp) => pp.number);
                    expect(
                        deck.filter((x) => URANIUM.includes(x)),
                        label
                    ).to.be.empty;
                    expect(deck.length, label).to.equal(G.powerPlantsDeck.length);
                    if (G.step < 3) {
                        expect(
                            deck.filter((x) => SET_ASIDE.includes(x)),
                            label
                        ).to.be.empty;
                        expect(s.setAsidePlants!.map((pp) => pp.number)).to.deep.equal(SET_ASIDE);
                    } else {
                        // The set-aside plants still in the deck are on top, in order, as in the real game.
                        const real = G.powerPlantsDeck.map((pp) => pp.number).filter((x) => SET_ASIDE.includes(x));
                        expect(deck.slice(0, real.length), label).to.deep.equal(real);
                        for (const pp of s.powerPlantsDeck) {
                            const printed = powerPlants.find((c) => c.number == pp.number)!.citiesPowered;
                            expect(pp.citiesPowered).to.equal(printed + (pp.type == PowerPlantType.Wind ? 1 : 0));
                        }
                    }
                }
            });
        }
    });

    describe('whole games', () => {
        for (const variant of ['original', 'recharged'] as const) {
            it(`${variant}: seeded games end at 2-6 players and replay exactly`, () => {
                for (const n of [2, 3, 4, 5, 6]) {
                    for (let i = 0; i < 3; i++) {
                        const G = playUntil(
                            setup(n, { map: 'Chile', variant }, `game-${variant}-${n}-${i}`),
                            `moves-${i}`
                        );
                        expect(ended(G), `${n}P game ${i}`).to.be.true;
                        expect(G.uraniumMarket + G.uraniumSupply).to.equal(0);
                        const replayed = reconstructState(cloneDeep(G));
                        expect(replayed.players.map((p) => [p.money, p.cities.length])).to.deep.equal(
                            G.players.map((p) => [p.money, p.cities.length])
                        );
                        expect(replayed.log.length).to.equal(G.log.length);
                    }
                }
            });
        }
    });
});
