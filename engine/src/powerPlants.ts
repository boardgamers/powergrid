import { cloneDeep } from 'lodash';
import { GameOptions, PowerPlant, PowerPlantDeck, PowerPlantType, SingleDeck } from './gamestate';
import { shuffle } from './utils';

const powerPlants: PowerPlant[] = [
    { number: 3, type: PowerPlantType.Oil, cost: 2, citiesPowered: 1 },
    { number: 4, type: PowerPlantType.Coal, cost: 2, citiesPowered: 1 },
    { number: 5, type: PowerPlantType.Hybrid, cost: 2, citiesPowered: 1 },
    { number: 6, type: PowerPlantType.Garbage, cost: 1, citiesPowered: 1 },
    { number: 7, type: PowerPlantType.Oil, cost: 3, citiesPowered: 2 },
    { number: 8, type: PowerPlantType.Coal, cost: 3, citiesPowered: 2 },
    { number: 9, type: PowerPlantType.Oil, cost: 1, citiesPowered: 1 },
    { number: 10, type: PowerPlantType.Coal, cost: 2, citiesPowered: 2 },
    { number: 11, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 2 },
    { number: 12, type: PowerPlantType.Hybrid, cost: 2, citiesPowered: 2 },
    { number: 13, type: PowerPlantType.Wind, cost: 0, citiesPowered: 1 },
    { number: 14, type: PowerPlantType.Garbage, cost: 2, citiesPowered: 2 },
    { number: 15, type: PowerPlantType.Coal, cost: 2, citiesPowered: 3 },
    { number: 16, type: PowerPlantType.Oil, cost: 2, citiesPowered: 3 },
    { number: 17, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 2 },
    { number: 18, type: PowerPlantType.Wind, cost: 0, citiesPowered: 2 },
    { number: 19, type: PowerPlantType.Garbage, cost: 2, citiesPowered: 3 },
    { number: 20, type: PowerPlantType.Coal, cost: 3, citiesPowered: 5 },
    { number: 21, type: PowerPlantType.Hybrid, cost: 2, citiesPowered: 4 },
    { number: 22, type: PowerPlantType.Wind, cost: 0, citiesPowered: 2 },
    { number: 23, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 3 },
    { number: 24, type: PowerPlantType.Garbage, cost: 2, citiesPowered: 4 },
    { number: 25, type: PowerPlantType.Coal, cost: 2, citiesPowered: 5 },
    { number: 26, type: PowerPlantType.Oil, cost: 2, citiesPowered: 5 },
    { number: 27, type: PowerPlantType.Wind, cost: 0, citiesPowered: 3 },
    { number: 28, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 4 },
    { number: 29, type: PowerPlantType.Hybrid, cost: 1, citiesPowered: 4 },
    { number: 30, type: PowerPlantType.Garbage, cost: 3, citiesPowered: 6 },
    { number: 31, type: PowerPlantType.Coal, cost: 3, citiesPowered: 6 },
    { number: 32, type: PowerPlantType.Oil, cost: 3, citiesPowered: 6 },
    { number: 33, type: PowerPlantType.Wind, cost: 0, citiesPowered: 4 },
    { number: 34, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 5 },
    { number: 35, type: PowerPlantType.Oil, cost: 1, citiesPowered: 5 },
    { number: 36, type: PowerPlantType.Coal, cost: 3, citiesPowered: 7 },
    { number: 37, type: PowerPlantType.Wind, cost: 0, citiesPowered: 4 },
    { number: 38, type: PowerPlantType.Garbage, cost: 3, citiesPowered: 7 },
    { number: 39, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 6 },
    { number: 40, type: PowerPlantType.Oil, cost: 2, citiesPowered: 6 },
    { number: 42, type: PowerPlantType.Coal, cost: 2, citiesPowered: 6 },
    { number: 44, type: PowerPlantType.Wind, cost: 0, citiesPowered: 5 },
    { number: 46, type: PowerPlantType.Hybrid, cost: 3, citiesPowered: 7 },
    { number: 50, type: PowerPlantType.Nuclear, cost: 0, citiesPowered: 6 },
    { number: 99, type: PowerPlantType.Step3, cost: 0, citiesPowered: 6 },
];

// Deck 2, The New Power Plants – Set 2 (the "alternate" deck): the same card
// numbers as the standard deck, with different fuels and outputs. Plants 8, 22
// and 35 burn any mix of garbage and oil.
const alternatePowerPlants: PowerPlant[] = [
    { number: 3, type: PowerPlantType.Coal, cost: 2, citiesPowered: 1 },
    { number: 4, type: PowerPlantType.Coal, cost: 2, citiesPowered: 1 },
    { number: 5, type: PowerPlantType.Garbage, cost: 2, citiesPowered: 1 },
    { number: 6, type: PowerPlantType.Oil, cost: 1, citiesPowered: 1 },
    { number: 7, type: PowerPlantType.Coal, cost: 1, citiesPowered: 1 },
    { number: 8, type: PowerPlantType.GarbageOilHybrid, cost: 3, citiesPowered: 2 },
    { number: 9, type: PowerPlantType.Coal, cost: 3, citiesPowered: 2 },
    { number: 10, type: PowerPlantType.Oil, cost: 2, citiesPowered: 2 },
    { number: 11, type: PowerPlantType.Wind, cost: 0, citiesPowered: 1 },
    { number: 12, type: PowerPlantType.Coal, cost: 2, citiesPowered: 2 },
    { number: 13, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 2 },
    { number: 14, type: PowerPlantType.Garbage, cost: 1, citiesPowered: 2 },
    { number: 15, type: PowerPlantType.Coal, cost: 1, citiesPowered: 2 },
    { number: 16, type: PowerPlantType.Garbage, cost: 2, citiesPowered: 3 },
    { number: 17, type: PowerPlantType.Wind, cost: 0, citiesPowered: 2 },
    { number: 18, type: PowerPlantType.Oil, cost: 2, citiesPowered: 3 },
    { number: 19, type: PowerPlantType.Garbage, cost: 1, citiesPowered: 3 },
    { number: 20, type: PowerPlantType.Coal, cost: 3, citiesPowered: 4 },
    { number: 21, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 3 },
    { number: 22, type: PowerPlantType.GarbageOilHybrid, cost: 3, citiesPowered: 5 },
    { number: 23, type: PowerPlantType.Oil, cost: 2, citiesPowered: 4 },
    { number: 24, type: PowerPlantType.Wind, cost: 0, citiesPowered: 3 },
    { number: 25, type: PowerPlantType.Coal, cost: 2, citiesPowered: 5 },
    { number: 26, type: PowerPlantType.Garbage, cost: 1, citiesPowered: 4 },
    { number: 27, type: PowerPlantType.Coal, cost: 1, citiesPowered: 4 },
    { number: 28, type: PowerPlantType.Wind, cost: 0, citiesPowered: 3 },
    { number: 29, type: PowerPlantType.Coal, cost: 2, citiesPowered: 5 },
    { number: 30, type: PowerPlantType.Oil, cost: 2, citiesPowered: 5 },
    { number: 31, type: PowerPlantType.Wind, cost: 0, citiesPowered: 4 },
    { number: 32, type: PowerPlantType.Uranium, cost: 2, citiesPowered: 5 },
    { number: 33, type: PowerPlantType.Coal, cost: 3, citiesPowered: 6 },
    { number: 34, type: PowerPlantType.Garbage, cost: 3, citiesPowered: 6 },
    { number: 35, type: PowerPlantType.GarbageOilHybrid, cost: 2, citiesPowered: 5 },
    { number: 36, type: PowerPlantType.Wind, cost: 0, citiesPowered: 5 },
    { number: 37, type: PowerPlantType.Uranium, cost: 2, citiesPowered: 6 },
    { number: 38, type: PowerPlantType.Oil, cost: 3, citiesPowered: 6 },
    { number: 39, type: PowerPlantType.Garbage, cost: 2, citiesPowered: 6 },
    { number: 40, type: PowerPlantType.Coal, cost: 2, citiesPowered: 6 },
    { number: 42, type: PowerPlantType.Oil, cost: 2, citiesPowered: 6 },
    { number: 44, type: PowerPlantType.Wind, cost: 0, citiesPowered: 6 },
    { number: 46, type: PowerPlantType.Garbage, cost: 2, citiesPowered: 7 },
    { number: 50, type: PowerPlantType.Uranium, cost: 2, citiesPowered: 7 },
    { number: 99, type: PowerPlantType.Step3, cost: 0, citiesPowered: 6 },
];

// Deck 1, The New Power Plants (Set 1 in Recharged), as its Variant 1 plays it:
// the big plants 52, 54, 57 and 60 stay in the box. Hybrids burn coal and oil;
// 44 is a fusion plant.
const deck1PowerPlants: PowerPlant[] = [
    { number: 1, type: PowerPlantType.Coal, cost: 3, citiesPowered: 1 },
    { number: 2, type: PowerPlantType.Oil, cost: 2, citiesPowered: 1 },
    { number: 3, type: PowerPlantType.Coal, cost: 1, citiesPowered: 1 },
    { number: 4, type: PowerPlantType.Hybrid, cost: 1, citiesPowered: 1 },
    { number: 5, type: PowerPlantType.Hybrid, cost: 3, citiesPowered: 2 },
    { number: 6, type: PowerPlantType.Garbage, cost: 1, citiesPowered: 2 },
    { number: 7, type: PowerPlantType.Oil, cost: 2, citiesPowered: 2 },
    { number: 8, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 2 },
    { number: 9, type: PowerPlantType.Coal, cost: 3, citiesPowered: 3 },
    { number: 10, type: PowerPlantType.Wind, cost: 0, citiesPowered: 1 },
    { number: 11, type: PowerPlantType.Wind, cost: 0, citiesPowered: 1 },
    { number: 12, type: PowerPlantType.Oil, cost: 1, citiesPowered: 2 },
    { number: 13, type: PowerPlantType.Hybrid, cost: 1, citiesPowered: 2 },
    { number: 14, type: PowerPlantType.Coal, cost: 3, citiesPowered: 4 },
    { number: 15, type: PowerPlantType.Wind, cost: 0, citiesPowered: 2 },
    { number: 16, type: PowerPlantType.Wind, cost: 0, citiesPowered: 2 },
    { number: 19, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 3 },
    { number: 20, type: PowerPlantType.Oil, cost: 1, citiesPowered: 3 },
    { number: 21, type: PowerPlantType.Garbage, cost: 3, citiesPowered: 5 },
    { number: 22, type: PowerPlantType.Oil, cost: 2, citiesPowered: 4 },
    { number: 23, type: PowerPlantType.Coal, cost: 2, citiesPowered: 4 },
    { number: 24, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 4 },
    { number: 25, type: PowerPlantType.Oil, cost: 3, citiesPowered: 5 },
    { number: 26, type: PowerPlantType.Wind, cost: 0, citiesPowered: 3 },
    { number: 27, type: PowerPlantType.Garbage, cost: 1, citiesPowered: 4 },
    { number: 28, type: PowerPlantType.Coal, cost: 3, citiesPowered: 5 },
    { number: 29, type: PowerPlantType.Hybrid, cost: 3, citiesPowered: 5 },
    { number: 30, type: PowerPlantType.Coal, cost: 1, citiesPowered: 4 },
    { number: 31, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 5 },
    { number: 32, type: PowerPlantType.Wind, cost: 0, citiesPowered: 4 },
    { number: 33, type: PowerPlantType.Garbage, cost: 2, citiesPowered: 5 },
    { number: 34, type: PowerPlantType.Coal, cost: 3, citiesPowered: 6 },
    { number: 35, type: PowerPlantType.Coal, cost: 1, citiesPowered: 5 },
    { number: 36, type: PowerPlantType.Hybrid, cost: 2, citiesPowered: 6 },
    { number: 37, type: PowerPlantType.Oil, cost: 3, citiesPowered: 7 },
    { number: 38, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 6 },
    { number: 39, type: PowerPlantType.Wind, cost: 0, citiesPowered: 5 },
    { number: 40, type: PowerPlantType.Oil, cost: 1, citiesPowered: 6 },
    { number: 42, type: PowerPlantType.Garbage, cost: 2, citiesPowered: 7 },
    { number: 44, type: PowerPlantType.Nuclear, cost: 0, citiesPowered: 6 },
    { number: 46, type: PowerPlantType.Coal, cost: 2, citiesPowered: 7 },
    { number: 50, type: PowerPlantType.Uranium, cost: 2, citiesPowered: 8 },
    { number: 99, type: PowerPlantType.Step3, cost: 0, citiesPowered: 6 },
];

// The maps the legacy alternatePowerPlants option was honoured on. Games created
// with it keep exactly that behaviour; new games pick a deck with powerPlantDeck.
const ALTERNATE_DECK_MAPS: string[] = ['Europe', 'North America'];

function usesAlternateDeck(mapName: string, alternate: boolean | undefined): boolean {
    return !!alternate && ALTERNATE_DECK_MAPS.includes(mapName);
}

// India's version of a deck: one plant leaves the game, and garbage plants cost one
// more garbage to run but have no additional storage.
function indiaCatalogue(deck: PowerPlant[], removed: number[]): PowerPlant[] {
    const plants = cloneDeep(deck).filter((pp) => !removed.includes(pp.number));
    plants.forEach((pp) => {
        if (pp.type == PowerPlantType.Garbage) {
            pp.storage = 2 * pp.cost;
            pp.cost++;
        }
    });
    return plants;
}

const indiaPowerPlants = indiaCatalogue(powerPlants, [11]);
const indiaCatalogues: Record<SingleDeck, PowerPlant[]> = {
    standard: indiaPowerPlants,
    deck1: indiaCatalogue(deck1PowerPlants, [8]),
    deck2: indiaCatalogue(alternatePowerPlants, [13]),
};

// The shuffled decks hold copies of the same number. The standard deck's copy keeps
// its number; Deck 1's and Deck 2's copies get .1 and .2, so each copy has its own
// number and the market ranks duplicates Deck 2 > Deck 1 > Original. plantLabel()
// prints them as "46 (Deck 2)"; rules compare the printed number.
const shuffledPowerPlants: PowerPlant[] = [
    ...powerPlants.filter((pp) => pp.type != PowerPlantType.Step3),
    ...deck1PowerPlants
        .filter((pp) => pp.type != PowerPlantType.Step3)
        .map((pp) => ({ ...pp, number: pp.number + 0.1 })),
    ...alternatePowerPlants
        .filter((pp) => pp.type != PowerPlantType.Step3)
        .map((pp) => ({ ...pp, number: pp.number + 0.2 })),
]
    .sort((a, b) => a.number - b.number)
    .concat(powerPlants.filter((pp) => pp.type == PowerPlantType.Step3));

// India's shuffled decks: the removed plants leave once dealt (see removedPlants).
const indiaShuffledPowerPlants = indiaCatalogue(shuffledPowerPlants, []);

// Which deck a plant's copy came from in the shuffled decks: 0 standard, 1, or 2.
function plantCopy(number: number): number {
    return Math.round((number - Math.floor(number)) * 10);
}

// A plant number as printed on the card, marking the shuffled decks' extra copies.
function plantLabel(number: number | undefined): string {
    if (number === undefined) return `${number}`;
    const copy = plantCopy(number);
    return copy ? `${Math.floor(number)} (Deck ${copy})` : `${number}`;
}

// Matches a plantLabel() in log text: group 1 is the printed number, group 2 the copy.
const PLANT_LABEL_PATTERN = String.raw`(\d+)(?: \(Deck ([12])\))?`;

function labelledPlant(printed: string, copy: string | undefined): number {
    return Number(printed) + (copy ? Number(copy) / 10 : 0);
}

// The decks a map can be played with: every map takes every deck. The shuffled decks
// follow every deck's map rules at once (see deckChanges.ts); where those clash, the
// map's setup states the rule by its purpose (Northern Europe's regional cards in
// applyRegionalPowerPlants, Québec's top of the deck, Original Russia's opening).
function availableDecks(): PowerPlantDeck[] {
    return ['standard', 'deck1', 'deck2', 'shuffled', 'shuffledUnique'];
}

// The deck a game plays with. Games from before powerPlantDeck may carry the
// legacy alternatePowerPlants flag, which setup only stored where it applied.
function gameDeck(options: GameOptions): PowerPlantDeck {
    return (
        (options.powerPlantDeck as PowerPlantDeck | undefined) ?? (options.alternatePowerPlants ? 'deck2' : 'standard')
    );
}

// The full card list a game on this map draws from. A 'shuffledUnique' game deals
// a subset of it (see dealtCatalogue), so lookups by number still work.
function plantCatalogue(mapName: string, deck: PowerPlantDeck = 'standard'): PowerPlant[] {
    if (deck == 'shuffled' || deck == 'shuffledUnique') {
        return mapName == 'India' ? indiaShuffledPowerPlants : shuffledPowerPlants;
    }
    if (mapName == 'India') {
        return indiaCatalogues[deck];
    }

    return deck == 'deck1' ? deck1PowerPlants : deck == 'deck2' ? alternatePowerPlants : powerPlants;
}

// A sampled 'shuffled' game deals as many plug and socket cards as the standard deck has.
const STANDARD_PLUG_PLANTS = powerPlants.filter(
    (pp) => pp.type != PowerPlantType.Step3 && isPlugPlant(pp, 'standard')
).length;
const STANDARD_SOCKET_PLANTS =
    powerPlants.filter((pp) => pp.type != PowerPlantType.Step3).length - STANDARD_PLUG_PLANTS;

// The plants a game is dealt from: the catalogue; for 'shuffledUnique' one random
// copy of each number; for a sampled 'shuffled' game a standard-sized random draw
// from all three decks. The Step 3 card stays last.
function dealtCatalogue(mapName: string, deck: PowerPlantDeck, rng: () => number, sample = false): PowerPlant[] {
    const catalogue = plantCatalogue(mapName, deck);
    if (deck == 'shuffled' && sample) {
        const plants = catalogue.filter((pp) => pp.type != PowerPlantType.Step3);
        const plug = shuffle(
            plants.filter((pp) => isPlugPlant(pp, deck)),
            rng() + ''
        ).slice(0, STANDARD_PLUG_PLANTS);
        const socket = shuffle(
            plants.filter((pp) => !isPlugPlant(pp, deck)),
            rng() + ''
        ).slice(0, STANDARD_SOCKET_PLANTS);
        return [...plug, ...socket]
            .sort((a, b) => a.number - b.number)
            .concat(catalogue.filter((pp) => pp.type == PowerPlantType.Step3));
    }
    if (deck != 'shuffledUnique') {
        return catalogue;
    }
    const copies = new Map<number, PowerPlant[]>();
    for (const pp of catalogue) {
        copies.set(Math.floor(pp.number), [...(copies.get(Math.floor(pp.number)) ?? []), pp]);
    }
    return [...copies.values()].map((options) => options[Math.floor(rng() * options.length)]);
}

// Plants with a plug on the back form the weak opening pool: 03–15 in the
// standard and alternate decks, 01–16 in Deck 1. Only for the single decks.
function lastPlugPlant(deck: PowerPlantDeck): number {
    return deck == 'deck1' ? 16 : 15;
}

// Whether a plant has a plug on the back, in any deck: Deck 1's copies are plug
// cards up to 16, the others up to 15.
function isPlugPlant(pp: { number: number }, deck: PowerPlantDeck): boolean {
    const fromDeck1 =
        deck == 'deck1' || ((deck == 'shuffled' || deck == 'shuffledUnique') && plantCopy(pp.number) == 1);
    return Math.floor(pp.number) <= (fromDeck1 ? 16 : 15);
}

// The nuclear plant whose purchase ends uranium resupply in Recharged Germany and
// Italy: Germany's per each deck's map-changes sheet, and Italy ends the same way.
// In the shuffled decks each deck's copy keeps its own trigger.
const PHASE_OUT_PLANT: Record<SingleDeck, number> = { standard: 39, deck1: 38, deck2: 37 };

function phaseOutPlants(deck: PowerPlantDeck): number[] {
    return deck == 'shuffled' || deck == 'shuffledUnique' ? [39, 38.1, 37.2] : [PHASE_OUT_PLANT[deck]];
}

// Wind plants are always ecological. Whether fusion plants are too is a ruling:
// new games take this value and store it as options.fusionEcological on the maps
// in ECOLOGICAL_RULE_MAPS, so changing it only affects games created afterwards.
const FUSION_IS_ECOLOGICAL = false;

// The maps whose rules single out ecological plants: Benelux's extra market slot
// and Québec's protected plants.
const ECOLOGICAL_RULE_MAPS: string[] = ['Benelux', 'Quebec'];

function isEcological(pp: PowerPlant, fusionEcological: boolean | undefined): boolean {
    return pp.type == PowerPlantType.Wind || (!!fusionEcological && pp.type == PowerPlantType.Nuclear);
}

export {
    powerPlants,
    indiaPowerPlants,
    alternatePowerPlants,
    deck1PowerPlants,
    ALTERNATE_DECK_MAPS,
    usesAlternateDeck,
    availableDecks,
    gameDeck,
    plantCatalogue,
    dealtCatalogue,
    plantCopy,
    plantLabel,
    PLANT_LABEL_PATTERN,
    labelledPlant,
    lastPlugPlant,
    isPlugPlant,
    PHASE_OUT_PLANT,
    phaseOutPlants,
    FUSION_IS_ECOLOGICAL,
    ECOLOGICAL_RULE_MAPS,
    isEcological,
};
