import { expect } from 'chai';
import { range } from 'lodash';
import 'mocha';
import { availableMoves } from './available-moves';
import { QUEBEC_RECHARGED_TOP_PLANTS, removedPlants, SPAIN_STEP_2_PLANTS } from './deckChanges';
import { ended, move, moveAI, setup, updatePlayerCapacity } from './engine';
import { GameState, MapName, Phase, PowerPlantDeck, PowerPlantType, ResourceType, Variant } from './gamestate';
import { maps, mapsRecharged } from './maps';
import { Move, MoveName } from './move';
import {
    alternatePowerPlants,
    deck1PowerPlants,
    isPlugPlant,
    labelledPlant,
    NUMBERED_SETUP_MAPS,
    plantCatalogue,
    plantLabel,
    powerPlants,
} from './powerPlants';

const numbers = (plants: { number: number }[]) => plants.map((pp) => pp.number);
const visible = (G: GameState) => [...G.actualMarket, ...G.futureMarket, ...G.powerPlantsDeck];
const catalogues = { standard: powerPlants, deck1: deck1PowerPlants, deck2: alternatePowerPlants };

describe('power plant decks', () => {
    it('deals Deck 1 in the Original edition from plants 01–08, with 11 on top', () => {
        for (const players of [2, 3, 4, 5]) {
            const G = setup(players, { map: 'Germany', variant: 'original', powerPlantDeck: 'deck1' }, 'deck1');
            expect(numbers(G.actualMarket)).to.deep.equal([1, 2, 3, 4]);
            expect(numbers(G.futureMarket)).to.deep.equal([5, 6, 7, 8]);
            expect(G.powerPlantsDeck[0].number).to.equal(11);
            expect(G.powerPlantsDeck[G.powerPlantsDeck.length - 1].number).to.equal(99);
            expect(G.options.powerPlantDeck).to.equal('deck1');
        }
    });

    it('deals each deck in the Recharged edition from its own plug cards', () => {
        for (const [deck, lastPlug] of [
            ['deck1', 16],
            ['deck2', 15],
            ['standard', 15],
        ] as [PowerPlantDeck, number][]) {
            for (const seed of range(10).map(String)) {
                const G = setup(4, { map: 'USA', variant: 'recharged', powerPlantDeck: deck }, seed);
                const market = [...G.actualMarket, ...G.futureMarket];
                expect(
                    market.every((pp) => pp.number <= lastPlug),
                    `${deck} ${seed}`
                ).to.be.true;
                expect(G.powerPlantsDeck[0].number).to.be.at.most(lastPlug);
                for (const pp of visible(G)) {
                    expect(pp, `${deck} ${pp.number}`).to.deep.equal(
                        catalogues[deck].find((c) => c.number == pp.number)
                    );
                }
            }
        }
    });

    it('stores the deck only when it is not the standard one', () => {
        expect(setup(3, { map: 'USA' }, 's').options).to.not.have.property('powerPlantDeck');
        expect(setup(3, { map: 'USA', powerPlantDeck: 'standard' }, 's').options).to.not.have.property(
            'powerPlantDeck'
        );
        expect(setup(3, { map: 'Korea', powerPlantDeck: 'deck2' }, 's').options.powerPlantDeck).to.equal('deck2');
    });

    it('offers every deck on every map', () => {
        for (const variant of ['original', 'recharged'] as Variant[]) {
            for (const map of (variant == 'original' ? maps : mapsRecharged).map((m) => m.name as MapName)) {
                for (const deck of ['deck1', 'deck2'] as PowerPlantDeck[]) {
                    const G = setup(4, { map, variant, powerPlantDeck: deck }, 'every-map');
                    expect(G.options.powerPlantDeck, `${map} ${variant} ${deck}`).to.equal(deck);
                }
            }
        }
    });

    it('resolves a random deck from the seed, without shifting the rest of the setup', () => {
        const picked = new Set<string>();
        for (const seed of range(30).map(String)) {
            const G = setup(4, { map: 'Germany', variant: 'recharged', powerPlantDeck: 'random' }, seed);
            const resolved = (G.options.powerPlantDeck ?? 'standard') as PowerPlantDeck;
            picked.add(resolved);
            const direct = setup(4, { map: 'Germany', variant: 'recharged', powerPlantDeck: resolved }, seed);
            expect(JSON.stringify(G)).to.equal(JSON.stringify(direct));
        }
        expect([...picked].sort()).to.deep.equal(['deck1', 'deck2', 'standard']);
    });

    it('keeps the legacy alternate deck flag working where it applied', () => {
        const legacy = setup(4, { map: 'Europe', variant: 'recharged', alternatePowerPlants: true }, 'legacy');
        expect(legacy.options.alternatePowerPlants).to.equal(true);
        expect(legacy.options).to.not.have.property('powerPlantDeck');
        expect(legacy.players[0].garbageOilHybridCapacity).to.equal(0);
        for (const pp of visible(legacy)) {
            expect(pp).to.deep.equal(alternatePowerPlants.find((c) => c.number == pp.number));
        }

        const ignored = setup(4, { map: 'Germany', alternatePowerPlants: true }, 'legacy');
        expect(ignored.options).to.not.have.property('alternatePowerPlants');
        expect(ignored.options).to.not.have.property('powerPlantDeck');

        const overridden = setup(4, { map: 'Europe', alternatePowerPlants: true, powerPlantDeck: 'deck1' }, 'legacy');
        expect(overridden.options).to.not.have.property('alternatePowerPlants');
        expect(overridden.options.powerPlantDeck).to.equal('deck1');
    });

    it("ends Germany's and Italy's uranium resupply on each deck's own nuclear plant", () => {
        for (const map of ['Germany', 'Italy'] as MapName[])
            for (const [deck, plant] of [
                ['standard', 39],
                ['deck1', 38],
                ['deck2', 37],
            ] as [PowerPlantDeck, number][]) {
                for (const [number, triggers] of [
                    [plant, true],
                    [plant == 39 ? 38 : 39, false],
                ] as [number, boolean][]) {
                    const G = setup(3, { map, variant: 'recharged', powerPlantDeck: deck }, 'phase-out');
                    G.actualMarket[0] = catalogues[deck].find((c) => c.number == number)!;
                    const player = G.currentPlayers[0];
                    G.players[player].money = 100;
                    G.players[player].availableMoves = availableMoves(G, G.players[player]);
                    const after = move(G, { name: MoveName.ChoosePowerPlant, data: number } as Move, player);
                    expect(after.card39Bought, `${map} ${deck} ${number}`).to.equal(triggers);
                }
            }
    });

    for (const [map, variant, deck] of [
        ['Germany', 'recharged', 'deck1'],
        ['USA', 'original', 'deck1'],
        ['Benelux', 'recharged', 'deck2'],
        ['Japan', 'original', 'deck2'],
    ] as [MapName, Variant, PowerPlantDeck][]) {
        it(`plays a whole bot game on ${map} ${variant} with ${deck} and replays it`, () => {
            let G = setup(4, { map, variant, powerPlantDeck: deck }, `bots-${map}-${deck}`);
            G.players.forEach((p, i) => {
                p.name = `AI ${i}`;
                p.isAI = true;
            });
            for (let turn = 0; turn < 5000 && !ended(G) && G.currentPlayers.length > 0; turn++) {
                G = moveAI(G, G.currentPlayers[0]);
            }
            expect(ended(G), 'game finished').to.be.true;

            let replay = setup(4, G.options, G.seed);
            replay.players.forEach((p, i) => {
                p.name = `AI ${i}`;
                p.isAI = true;
            });
            for (const item of G.log) {
                if (item.type === 'move') replay = move(replay, item.move, item.player);
            }
            expect(replay.players.map((p) => p.money)).to.deep.equal(G.players.map((p) => p.money));
            expect(replay.players.map((p) => p.citiesPowered)).to.deep.equal(G.players.map((p) => p.citiesPowered));
        });
    }
});

describe('power plant decks on maps with deck-specific changes', () => {
    const decks: PowerPlantDeck[] = ['deck1', 'deck2'];
    const variants: Variant[] = ['original', 'recharged'];
    const seeds = range(6).map(String);

    it("leaves each deck's removed plants out and deals only that deck's cards", () => {
        const maps: MapName[] = [
            'France',
            'Russia',
            'Australia',
            'India',
            'South Africa',
            'Spain & Portugal',
            'Bremen',
            'Manhattan',
            'China',
            'Brazil',
            'Quebec',
            'UK & Ireland',
            'Middle East',
        ];
        for (const map of maps) {
            for (const deck of decks) {
                for (const variant of variants) {
                    for (const players of [2, 3, 4, 5]) {
                        const G = setup(players, { map, variant, powerPlantDeck: deck }, `removed-${players}`);
                        const label = `${map} ${variant} ${deck} ${players}P`;
                        expect(G.options.powerPlantDeck, label).to.equal(deck);
                        const dealt = numbers(visible(G));
                        for (const removed of removedPlants(map, deck, players, variant)) {
                            expect(dealt, label).to.not.include(removed);
                        }
                        expect(new Set(dealt).size, `${label} has no duplicates`).to.equal(dealt.length);
                        const catalogue = plantCatalogue(map, deck);
                        for (const pp of visible(G)) {
                            expect(pp, `${label} ${pp.number}`).to.deep.equal(
                                catalogue.find((c) => c.number == pp.number)
                            );
                        }
                    }
                }
            }
        }
    });

    it("opens the France market with each deck's nuclear plant", () => {
        for (const seed of seeds) {
            const deck1 = setup(4, { map: 'France', variant: 'recharged', powerPlantDeck: 'deck1' }, seed);
            expect(numbers([...deck1.actualMarket, ...deck1.futureMarket])).to.include(8);
            const deck2 = setup(4, { map: 'France', variant: 'recharged', powerPlantDeck: 'deck2' }, seed);
            expect(numbers([...deck2.actualMarket, ...deck2.futureMarket])).to.include(13);
        }
        // Original: Deck 1 just loses plant 11 (its nuclear 08 opens the market); Deck 2's 13 goes on top.
        const original1 = setup(4, { map: 'France', variant: 'original', powerPlantDeck: 'deck1' }, 'o');
        expect(numbers(original1.actualMarket.concat(original1.futureMarket))).to.deep.equal([1, 2, 3, 4, 5, 6, 7, 8]);
        expect(numbers(visible(original1))).to.not.include(11);
        const original2 = setup(4, { map: 'France', variant: 'original', powerPlantDeck: 'deck2' }, 'o');
        expect(original2.powerPlantsDeck[0].number).to.equal(13);
    });

    it('opens the Brazil market with the low biogas plants and keeps every biogas plant', () => {
        for (const seed of seeds) {
            for (const [deck, opening] of [
                ['deck1', [6]],
                ['deck2', [5, 14]],
            ] as [PowerPlantDeck, number[]][]) {
                const G = setup(2, { map: 'Brazil', variant: 'recharged', powerPlantDeck: deck }, seed);
                const market = numbers([...G.actualMarket, ...G.futureMarket]);
                for (const number of opening) expect(market, `${deck} ${seed}`).to.include(number);
                const garbage = plantCatalogue('Brazil', deck).filter((pp) => pp.type == PowerPlantType.Garbage);
                for (const pp of garbage) expect(numbers(visible(G)), `${deck} ${seed}`).to.include(pp.number);
            }
        }
    });

    it("sets up Québec with each deck's ecological plants", () => {
        for (const seed of seeds) {
            const deck1 = setup(2, { map: 'Quebec', variant: 'recharged', powerPlantDeck: 'deck1' }, seed);
            expect(numbers([...deck1.actualMarket, ...deck1.futureMarket])).to.include.members([11, 15, 16]);
            const deck2 = setup(2, { map: 'Quebec', variant: 'recharged', powerPlantDeck: 'deck2' }, seed);
            expect(numbers([...deck2.actualMarket, ...deck2.futureMarket])).to.include(11);
            expect(numbers(deck2.powerPlantsDeck.slice(0, 2))).to.deep.equal(QUEBEC_RECHARGED_TOP_PLANTS.deck2);
            for (const G of [deck1, deck2]) {
                const deck = G.options.powerPlantDeck as PowerPlantDeck;
                const wind = plantCatalogue('Quebec', deck).filter((pp) => pp.type == PowerPlantType.Wind);
                expect(numbers(visible(G))).to.include.members(numbers(wind));
            }
        }
        const original1 = setup(3, { map: 'Quebec', variant: 'original', powerPlantDeck: 'deck1' }, 'o');
        expect(numbers(original1.powerPlantsDeck.slice(0, 3))).to.deep.equal([11, 15, 16]);
        const original2 = setup(3, { map: 'Quebec', variant: 'original', powerPlantDeck: 'deck2' }, 'o');
        expect(numbers(original2.powerPlantsDeck.slice(0, 3))).to.deep.equal([11, 17, 24]);
    });

    it('opens China with the smallest remaining plants, one per player', () => {
        const deck1 = setup(3, { map: 'China', variant: 'recharged', powerPlantDeck: 'deck1' }, 'c');
        expect(numbers(deck1.actualMarket)).to.deep.equal([3, 4, 5]);
        const deck2 = setup(3, { map: 'China', variant: 'recharged', powerPlantDeck: 'deck2' }, 'c');
        expect(numbers(deck2.actualMarket)).to.deep.equal([4, 5, 7]);
    });

    it('holds the Spain & Portugal ecological plants back until Step 2', () => {
        for (const deck of decks) {
            let G = setup(4, { map: 'Spain & Portugal', variant: 'recharged', powerPlantDeck: deck }, `spain-${deck}`);
            G.players.forEach((p, i) => {
                p.name = `AI ${i}`;
                p.isAI = true;
            });
            const held = SPAIN_STEP_2_PLANTS[deck];
            for (const number of held) expect(numbers(visible(G)), deck).to.not.include(number);
            for (let turn = 0; turn < 5000 && G.step == 1 && G.currentPlayers.length > 0; turn++) {
                G = moveAI(G, G.currentPlayers[0]);
            }
            expect(G.step).to.equal(2);
            // The first replaces the plant removed at the start of Step 2; the other two follow.
            const known = numbers([...G.actualMarket, ...G.futureMarket, ...G.powerPlantsDeck.slice(0, 2)]);
            expect(known, deck).to.include.members(held);
        }
    });

    it("swaps Northern Europe's regional cards in by the map's numbers", () => {
        const regions = (G: GameState) => new Set(G.map.cities.map((city) => city.region));
        const G = range(40)
            .map((seed) =>
                setup(5, { map: 'Northern Europe', variant: 'recharged', powerPlantDeck: 'deck1' }, `${seed}`)
            )
            .find((game) => regions(game).has('yellow') && regions(game).has('pink'))!;
        expect(G, 'a game with Sweden North and the Baltic States').to.exist;
        const dealt = visible(G);
        const byNumber = (number: number) => dealt.filter((pp) => pp.number == number);
        // Sweden North's 21 and 25 replace Deck 1's; the Baltic 18, which Deck 1 lacks, is added.
        expect(byNumber(21).map((pp) => pp.type)).to.deep.equal([PowerPlantType.Wind]);
        expect(byNumber(25).map((pp) => pp.type)).to.deep.equal([PowerPlantType.Uranium]);
        expect(byNumber(18).map((pp) => pp.type)).to.deep.equal([PowerPlantType.Oil]);
        expect(G.powerPlantsDeck[G.powerPlantsDeck.length - 1].type).to.equal(PowerPlantType.Step3);
    });

    it('closes the garbage market in Middle East Step 1, even for Deck 2 hybrids', () => {
        const G = setup(3, { map: 'Middle East', variant: 'recharged', powerPlantDeck: 'deck2' }, 'me');
        const player = G.players[0];
        player.powerPlants = [alternatePowerPlants.find((pp) => pp.number == 8)!];
        player.powerPlantsNotUsed = [8];
        updatePlayerCapacity(player);
        player.money = 200;
        G.phase = Phase.Resources;
        const offered = (step: number) => {
            G.step = step;
            return (availableMoves(G, player)[MoveName.BuyResource] ?? []).map((r) => r.resource);
        };
        expect(offered(1)).to.include(ResourceType.Oil);
        expect(offered(1)).to.not.include(ResourceType.Garbage);
        expect(offered(2)).to.include(ResourceType.Garbage);
    });

    for (const [map, variant, deck] of [
        ['Russia', 'original', 'deck1'],
        ['China', 'recharged', 'deck2'],
        ['Brazil', 'recharged', 'deck1'],
        ['Quebec', 'original', 'deck2'],
        ['Middle East', 'recharged', 'deck2'],
        ['India', 'recharged', 'deck1'],
        ['Bremen', 'recharged', 'deck1'],
        ['Northern Europe', 'recharged', 'deck2'],
        ['Northern Europe', 'original', 'deck1'],
        ['Italy', 'recharged', 'deck1'],
    ] as [MapName, Variant, PowerPlantDeck][]) {
        it(`plays a whole bot game on ${map} ${variant} with ${deck} and replays it`, () => {
            let G = setup(4, { map, variant, powerPlantDeck: deck }, `bots-${map}-${deck}`);
            G.players.forEach((p, i) => {
                p.name = `AI ${i}`;
                p.isAI = true;
            });
            for (let turn = 0; turn < 8000 && !ended(G) && G.currentPlayers.length > 0; turn++) {
                G = moveAI(G, G.currentPlayers[0]);
            }
            expect(ended(G), 'game finished').to.be.true;

            let replay = setup(4, G.options, G.seed);
            replay.players.forEach((p, i) => {
                p.name = `AI ${i}`;
                p.isAI = true;
            });
            for (const item of G.log) {
                if (item.type === 'move') replay = move(replay, item.move, item.player);
            }
            expect(replay.players.map((p) => p.money)).to.deep.equal(G.players.map((p) => p.money));
        });
    }
});

describe('shuffled power plant decks', () => {
    const shuffled = plantCatalogue('USA', 'shuffled');
    const printed = (plants: { number: number }[]) => plants.map((pp) => Math.floor(pp.number));

    it('holds every plant of all three decks, extra copies numbered .1 and .2', () => {
        const step3 = shuffled.filter((pp) => pp.type == PowerPlantType.Step3);
        expect(step3.map((pp) => pp.number)).to.deep.equal([99]);
        expect(shuffled[shuffled.length - 1].number).to.equal(99);
        expect(new Set(numbers(shuffled)).size).to.equal(shuffled.length);
        for (const [source, offset] of [
            [powerPlants, 0],
            [deck1PowerPlants, 0.1],
            [alternatePowerPlants, 0.2],
        ] as [typeof powerPlants, number][]) {
            for (const pp of source.filter((c) => c.type != PowerPlantType.Step3)) {
                expect(shuffled.find((c) => c.number == pp.number + offset)).to.deep.equal({
                    ...pp,
                    number: pp.number + offset,
                });
            }
        }
        expect(numbers(shuffled)).to.deep.equal([...numbers(shuffled)].sort((a, b) => a - b));
    });

    it('labels the extra copies with their deck', () => {
        expect(plantLabel(46)).to.equal('46');
        expect(plantLabel(46.1)).to.equal('46 (Deck 1)');
        expect(plantLabel(46.2)).to.equal('46 (Deck 2)');
        expect(labelledPlant('46', '2')).to.equal(46.2);
        expect(labelledPlant('46', undefined)).to.equal(46);
    });

    it('is only offered on maps whose rules name no plant numbers', () => {
        for (const deck of ['shuffled', 'shuffledUnique'] as PowerPlantDeck[]) {
            for (const map of NUMBERED_SETUP_MAPS as MapName[]) {
                const G = setup(4, { map, variant: 'recharged', powerPlantDeck: deck }, 'blocked');
                expect(G.options, `${map} ${deck}`).to.not.have.property('powerPlantDeck');
            }
            for (const map of ['USA', 'Germany', 'Italy', 'Benelux', 'Europe', 'UK & Ireland'] as MapName[]) {
                const G = setup(4, { map, variant: 'recharged', powerPlantDeck: deck }, 'offered');
                expect(G.options.powerPlantDeck, `${map} ${deck}`).to.equal(deck);
            }
        }
    });

    it("opens the Recharged market from every deck's plug cards", () => {
        for (const seed of range(8).map(String)) {
            const G = setup(4, { map: 'USA', variant: 'recharged', powerPlantDeck: 'shuffled' }, seed);
            const market = [...G.actualMarket, ...G.futureMarket];
            expect(
                market.every((pp) => isPlugPlant(pp, 'shuffled')),
                seed
            ).to.be.true;
            expect(numbers(market)).to.deep.equal([...numbers(market)].sort((a, b) => a - b));
            expect(isPlugPlant(G.powerPlantsDeck[0], 'shuffled')).to.be.true;
            expect(G.powerPlantsDeck[G.powerPlantsDeck.length - 1].number).to.equal(99);
        }
        // Deck 1's 16 is a plug card; the standard deck's and Deck 2's are not.
        expect(isPlugPlant({ number: 16.1 }, 'shuffled')).to.be.true;
        expect(isPlugPlant({ number: 16 }, 'shuffled')).to.be.false;
        expect(isPlugPlant({ number: 16.2 }, 'shuffled')).to.be.false;
    });

    it('opens the Original market with the eight smallest plants and 13 on top', () => {
        const G = setup(4, { map: 'USA', variant: 'original', powerPlantDeck: 'shuffled' }, 'o');
        expect(numbers([...G.actualMarket, ...G.futureMarket])).to.deep.equal([1.1, 2.1, 3, 3.1, 3.2, 4, 4.1, 4.2]);
        expect(G.powerPlantsDeck[0].number).to.equal(13);
    });

    it('keeps one random copy of each number in the one-per-number deck', () => {
        const dealt = (seed: string) =>
            visible(setup(5, { map: 'USA', variant: 'recharged', powerPlantDeck: 'shuffledUnique' }, seed));
        const first = dealt('a');
        const once = printed(first);
        expect(new Set(once).size, 'one copy per number').to.equal(once.length);
        expect(new Set(once)).to.deep.equal(new Set(printed(shuffled)));
        expect(once.some((n) => n > 50 && n != 99)).to.be.false;
        expect(numbers(dealt('a')).sort()).to.deep.equal(numbers(first).sort());
        expect(numbers(dealt('b')).sort()).to.not.deep.equal(numbers(first).sort());
    });

    it('starts the bidding at the printed number and logs the copy', () => {
        const G = setup(3, { map: 'Germany', variant: 'original', powerPlantDeck: 'shuffled' }, 'bid');
        const copy = shuffled.find((pp) => pp.number == 46.2)!;
        G.actualMarket[0] = copy;
        const player = G.currentPlayers[0];
        G.players[player].money = 100;
        G.players[player].availableMoves = availableMoves(G, G.players[player]);
        expect(G.players[player].availableMoves![MoveName.ChoosePowerPlant]).to.include(46.2);
        const after = move(G, { name: MoveName.ChoosePowerPlant, data: 46.2 } as Move, player);
        expect(after.minimunBid).to.equal(46);
        expect(after.chosenPowerPlant).to.deep.equal(copy);
        const entry = after.log[after.log.length - 1];
        expect(entry.type == 'move' && entry.simple).to.contain('Power Plant 46 (Deck 2)');
    });

    it("ends Germany's uranium resupply on any deck's own nuclear plant", () => {
        for (const [number, triggers] of [
            [39, true],
            [38.1, true],
            [37.2, true],
            [38, false],
            [39.1, false],
        ] as [number, boolean][]) {
            const G = setup(3, { map: 'Germany', variant: 'recharged', powerPlantDeck: 'shuffled' }, 'phase-out');
            G.actualMarket[0] = shuffled.find((pp) => pp.number == number)!;
            const player = G.currentPlayers[0];
            G.players[player].money = 100;
            G.players[player].availableMoves = availableMoves(G, G.players[player]);
            const after = move(G, { name: MoveName.ChoosePowerPlant, data: number } as Move, player);
            expect(after.card39Bought, `${number}`).to.equal(triggers);
        }
    });

    for (const [map, variant, deck] of [
        ['USA', 'original', 'shuffled'],
        ['Germany', 'recharged', 'shuffledUnique'],
        ['Europe', 'recharged', 'shuffled'],
        ['UK & Ireland', 'original', 'shuffledUnique'],
        ['Benelux', 'recharged', 'shuffled'],
    ] as [MapName, Variant, PowerPlantDeck][]) {
        it(`plays a whole bot game on ${map} ${variant} with ${deck} and replays it`, () => {
            let G = setup(4, { map, variant, powerPlantDeck: deck }, `bots-${map}-${deck}`);
            G.players.forEach((p, i) => {
                p.name = `AI ${i}`;
                p.isAI = true;
            });
            for (let turn = 0; turn < 8000 && !ended(G) && G.currentPlayers.length > 0; turn++) {
                G = moveAI(G, G.currentPlayers[0]);
            }
            expect(ended(G), 'game finished').to.be.true;

            let replay = setup(4, G.options, G.seed);
            replay.players.forEach((p, i) => {
                p.name = `AI ${i}`;
                p.isAI = true;
            });
            for (const item of G.log) {
                if (item.type === 'move') replay = move(replay, item.move, item.player);
            }
            expect(replay.players.map((p) => p.money)).to.deep.equal(G.players.map((p) => p.money));
        });
    }
});
