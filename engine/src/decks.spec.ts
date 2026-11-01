import { expect } from 'chai';
import { range } from 'lodash';
import 'mocha';
import { availableMoves } from './available-moves';
import { ended, move, moveAI, setup } from './engine';
import { GameState, MapName, PowerPlantDeck, Variant } from './gamestate';
import { Move, MoveName } from './move';
import { alternatePowerPlants, deck1PowerPlants, powerPlants } from './powerPlants';

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

    it('falls back to the standard deck on maps that need deck-specific changes', () => {
        for (const map of ['France', 'China', 'Quebec', 'Italy'] as MapName[]) {
            const G = setup(3, { map, variant: 'recharged', powerPlantDeck: 'deck1' }, 'fallback');
            expect(G.options).to.not.have.property('powerPlantDeck');
            expect(visible(G).some((pp) => pp.number == 1)).to.be.false;
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

        const france = setup(4, { map: 'France', powerPlantDeck: 'random' }, 'r');
        expect(france.options).to.not.have.property('powerPlantDeck');
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

    it("ends Germany's uranium resupply on each deck's own nuclear plant", () => {
        for (const [deck, plant] of [
            ['standard', 39],
            ['deck1', 38],
            ['deck2', 37],
        ] as [PowerPlantDeck, number][]) {
            for (const [number, triggers] of [
                [plant, true],
                [plant == 39 ? 38 : 39, false],
            ] as [number, boolean][]) {
                const G = setup(3, { map: 'Germany', variant: 'recharged', powerPlantDeck: deck }, 'phase-out');
                G.actualMarket[0] = catalogues[deck].find((c) => c.number == number)!;
                const player = G.currentPlayers[0];
                G.players[player].money = 100;
                G.players[player].availableMoves = availableMoves(G, G.players[player]);
                const after = move(G, { name: MoveName.ChoosePowerPlant, data: number } as Move, player);
                expect(after.card39Bought, `${deck} ${number}`).to.equal(triggers);
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
