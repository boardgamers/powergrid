import { expect } from 'chai';
import 'mocha';
import { deckBuildText, DECK_BUILD_TEMPLATES } from './deckBuildText';
import { setup } from './engine';
import { GameOptions, MapName, PowerPlantDeck, PowerPlantType, Variant } from './gamestate';
import { maps } from './maps';
import { availableDecks } from './powerPlants';

// The text must name the plants the engine actually deals, so read the numbers back
// out of the generated sentences and compare them with real setups.
const listAfter = (sentences: string[], pattern: RegExp): number[] | undefined => {
    for (const sentence of sentences) {
        const match = pattern.exec(sentence);
        if (match) return match[1].split(', ').map(Number);
    }
    return undefined;
};

const singleDecks: PowerPlantDeck[] = ['standard', 'deck1', 'deck2'];
const seeds = ['a', 'b', 'c'];

describe('Deck build text', () => {
    it('fills every placeholder and uses only known templates', () => {
        const templates = Object.values(DECK_BUILD_TEMPLATES).map(
            (t) => new RegExp('^' + t.replace(/[.*+?^$()|[\]\\]/g, '\\$&').replace(/\\?\{p\d+\\?\}/g, '(.+)') + '$')
        );
        for (const map of maps) {
            for (const variant of ['original', 'recharged'] as Variant[]) {
                for (const deck of availableDecks()) {
                    for (const players of [2, 3, 4, 5, 6]) {
                        const options: GameOptions = { map: map.name as MapName, variant, powerPlantDeck: deck };
                        const { standard, map: notes } = deckBuildText(map.name, options, players);
                        for (const sentence of [...standard, ...notes]) {
                            expect(sentence, `${map.name} ${variant} ${deck}`).not.to.match(/\{p\d+\}|undefined|NaN/);
                            expect(
                                templates.some((t) => t.test(sentence)),
                                `${map.name} ${variant} ${deck}: ${sentence}`
                            ).to.equal(true);
                        }
                    }
                }
            }
        }
    });

    for (const map of maps) {
        for (const variant of ['original', 'recharged'] as Variant[]) {
            it(`names the plants ${map.name} ${variant} deals with each single deck`, () => {
                for (const deck of singleDecks) {
                    for (const players of [2, 3, 4, 5, 6]) {
                        const options: GameOptions = { map: map.name as MapName, variant, powerPlantDeck: deck };
                        const { standard, map: notes } = deckBuildText(map.name, options, players);
                        const label = `${map.name} ${variant} ${deck} ${players}P`;
                        for (const seed of seeds) {
                            const G = setup(players, options, seed);
                            const market = [...G.actualMarket, ...G.futureMarket].map((p) => p.number);
                            const inGame = [...market, ...G.powerPlantsDeck.map((p) => p.number)];

                            const removed = [
                                ...(listAfter(notes, /^Power plants? ([\d, ]+) (?:is|are) removed from the game/) ??
                                    []),
                                ...(listAfter(notes, /^Power plants ([\d, ]+) also go into the game box/) ?? []),
                            ];
                            for (const number of removed) expect(inGame, `${label}: ${number}`).not.to.include(number);

                            const always = listAfter(notes, /^Power plants? ([\d, ]+) always starts? in the market/);
                            for (const number of always ?? []) expect(market, `${label}: ${number}`).to.include(number);

                            const held = listAfter(notes, /^Power plants ([\d, ]+) are set aside at setup/);
                            for (const number of held ?? [])
                                expect(inGame, `${label}: ${number}`).not.to.include(number);

                            const mines = listAfter(notes, /^The uranium mines \(([\d, ]+)\)/);
                            if (mines) {
                                const uranium = G.powerPlantsDeck
                                    .concat(G.actualMarket, G.futureMarket)
                                    .filter((p) => p.type == PowerPlantType.Uranium);
                                // The player-count removal can take mines out of the deck too.
                                for (const p of uranium) expect(mines, label).to.include(p.number);
                            }

                            if (variant != 'original') continue;
                            const russia = notes.find((s) => s.startsWith('The market is '));
                            if (russia) {
                                const [current, future] = /^The market is ([\d, ]+) \/ ([\d, ]+)\./
                                    .exec(russia)!
                                    .slice(1)
                                    .map((list) => list.split(', ').map(Number));
                                expect(
                                    G.actualMarket.map((p) => p.number),
                                    label
                                ).to.deep.equal(current);
                                expect(
                                    G.futureMarket.map((p) => p.number),
                                    label
                                ).to.deep.equal(future);
                            } else if (!['China', 'Manhattan', 'Europe', 'Middle East'].includes(map.name)) {
                                const sentence = standard.find((s) => s.startsWith('The market is fixed'))!;
                                const [current, future] =
                                    /power plants ([\d, ]+) are the current market and ([\d, ]+) the future/
                                        .exec(sentence)!
                                        .slice(1)
                                        .map((list) => list.split(', ').map(Number));
                                expect(
                                    G.actualMarket.map((p) => p.number),
                                    label
                                ).to.deep.equal(current);
                                expect(
                                    G.futureMarket.map((p) => p.number),
                                    label
                                ).to.deep.equal(future);
                            }

                            // The plant on top of the deck: the map's own list where it gives one.
                            const top =
                                listAfter(
                                    notes,
                                    /^Power plants? ([\d, ]+) (?:is|are) set aside and then placed on top/
                                ) ??
                                listAfter(notes, /^Power plant ([\d, ]+) is placed on top of the deck in place/) ??
                                (notes.some((s) => s.startsWith('No power plant goes on top'))
                                    ? []
                                    : listAfter(standard, /^Power plant ([\d, ]+) goes on top of the deck and/));
                            // Middle East's Step 1 rule then refills the market from the top of the deck.
                            if (['China', 'Manhattan', 'Europe', 'Middle East'].includes(map.name) || !top?.length)
                                continue;
                            expect(G.powerPlantsDeck[0].number, label).to.equal(top[0]);
                        }
                    }
                }
            });
        }
    }
});
