import {
    originalTopPlants,
    QUEBEC_RECHARGED_TOP_PLANTS,
    rechargedMarketPlants,
    removedPlants,
    RUSSIA_ORIGINAL_NEXT_PLANTS,
    SPAIN_STEP_2_PLANTS,
} from './deckChanges';
import { GameOptions, PowerPlant, PowerPlantDeck, PowerPlantType, SingleDeck } from './gamestate';
import { gameDeck, isPlugPlant, plantCatalogue, plantCopy } from './powerPlants';

// The rules dialog's "Deck build" section, generated from the same tables the decks
// are dealt from, so it names the right plants for the deck in play. Each sentence is
// a template whose {pN} values are plant numbers: the viewer's catalogues translate
// the templates, so keep every one a single string constant.
export const DECK_BUILD_TEMPLATES = {
    shuffledSample: 'All three decks are shuffled together and a standard-sized deck is dealt from them.',
    shuffledFull: 'All three decks are shuffled together into one deck.',
    shuffledUnique: 'All three decks are shuffled together, keeping one random copy of each plant number.',
    shuffledLegend:
        'Lists with three parts give the Original deck / Deck 1 / Deck 2 plants; each rule applies only to the plants dealt into this game.',
    plugPlants:
        'The low power plants are the "plug plants" ({p0}), named for the plug on the back of the printed cards.',
    rechargedMarket:
        'Shuffle the low plants, draw 8 and sort them ascending: the 4 cheapest form the current market, the next 4 the future market.',
    rechargedTop: 'One of the remaining low plants goes face down on top of the draw deck.',
    rechargedRemoval:
        'Player-count removal: 2 players remove 1 low + 5 higher plants; 3 players remove 2 low + 6 higher; 4 players remove 1 low + 3 higher; 5-6 players remove none.',
    rechargedRest: 'The leftover low plants are shuffled into the deck, with the Step 3 card on the bottom.',
    originalMarket: 'The market is fixed: power plants {p0} are the current market and {p1} the future market.',
    originalMarketShuffled:
        'The 8 smallest plants dealt form the market: the 4 cheapest are the current market, the next 4 the future market.',
    originalSetAside:
        'Power plant {p0} and the Step 3 card are set aside and the rest of the deck is shuffled, then 8 random plants are removed for 2-3 players, 4 for 4 players, and none for 5-6 players.',
    originalSetAsideNone:
        'The Step 3 card is set aside and the rest of the deck is shuffled, then 8 random plants are removed for 2-3 players, 4 for 4 players, and none for 5-6 players.',
    originalTop: 'Power plant {p0} goes on top of the deck and the Step 3 card on the bottom.',
    originalTopIfDealt: 'Power plant {p0} goes on top of the deck if it was dealt, and the Step 3 card on the bottom.',
    originalTopNone: 'The Step 3 card goes on the bottom of the deck.',
    standardSetup: 'Otherwise standard setup.',
    removedOne: 'Power plant {p0} is removed from the game.',
    removedMany: 'Power plants {p0} are removed from the game.',
    noFurtherRemoval: 'No further power plants are removed for the number of players.',
    marketAlwaysOne:
        'Power plant {p0} always starts in the market; the rest of the market is drawn from the low plants.',
    marketAlwaysMany:
        'Power plants {p0} always start in the market; the rest of the market is drawn from the low plants.',
    australiaMines: 'The uranium mines ({p0}) stay in the deck.',
    brazilGarbage:
        'Garbage plants {p0}, the ones above the plug plants, are set aside during the player-count removal and shuffled back in, so no garbage plant ever leaves the game.',
    brazilOriginalGarbage: 'Garbage plants are excluded from the player-count removal and shuffled back in.',
    topInOrderOne: 'Power plant {p0} is set aside and then placed on top of the deck.',
    topInOrderMany: 'Power plants {p0} are set aside and then placed on top of the deck, in that order.',
    franceTopInPlace: 'Power plant {p0} is placed on top of the deck in place of the usual top plant.',
    franceNoTop: 'No power plant goes on top of the deck.',
    franceRemoval:
        'Removal by player count: 2 players remove 6 higher plants, 3 players remove 1 low and 6 higher, 4 players remove 3 higher.',
    bremenMarket:
        'The opening market of eight is drawn from the low plants; of the low plants left over, one is placed on top of the draw deck and the rest are shuffled into it, with the Step 3 card on the bottom.',
    chinaOrder:
        'The deck is ordered, not shuffled: the plants up to 30 in ascending order on top, then plants 31-35 shuffled together with the Step 3 card, then the plants from 36 up shuffled on the bottom.',
    chinaMarket: 'The starting market has one plant per player and the future market starts empty.',
    europeMarket:
        'The power plant market starts as 4 current + 5 future power plants (9 total), all drawn from the plug plants; the top card of the draw deck is never a plug plant.',
    manhattanPlug:
        'Plug plants are put in the game box at random until nine remain: 8 form the starting market and 1 goes on top of the deck.',
    manhattanRest: 'The rest of the deck is random with no plug plants. The Step 3 card is removed from the game.',
    manhattanBoxed: 'Power plants {p0} also go into the game box.',
    northernEuropeRegional:
        'The regions in play swap in regional versions of certain power plants (same numbers, different fuel or output).',
    northernEuropeShuffled:
        'Each regional power plant in play takes the place of a dealt plant with its number, and every other dealt copy of that number leaves the game. A regional plant whose number was not dealt is shuffled into the deck.',
    quebecMarketFrom: 'The starting market is drawn from power plants {p0}.',
    quebecTopBeneath: 'One more low plant goes on top of the deck, with power plants {p0} directly beneath it.',
    quebecTopVery: 'Power plants {p0} go on the very top of the deck.',
    quebecEcological: 'Ecological plants are never removed during setup.',
    quebecEcologicalOriginal: 'Ecological plants are excluded from the player-count removal.',
    quebecShuffledRecharged:
        'One plug card goes on top of the deck, with the two smallest dealt ecological plants not in the market directly beneath it.',
    quebecShuffledOriginal:
        'Power plant {p0} goes on top of the deck if it was dealt, otherwise the smallest plug card left, with the two smallest dealt ecological plants not in the market directly beneath it.',
    russiaRechargedMarket:
        'The market has 6 plants (3 current, 3 future) drawn at random from the low plants; the undrawn low plants sit shuffled on top of the deck.',
    russiaRechargedRemoval:
        'Removal by player count (higher plants only): 2 players remove 6, 3 players remove 8, 4 players remove 4.',
    russiaOriginalMarket: 'The market is {p0} / {p1}.',
    russiaOriginalTop:
        'Power plant {p0} goes on top of the deck, then five shuffled cards (plants {p1} and the top three of the deck), then the rest, with the Step 3 card on the bottom.',
    russiaShuffledMarket: 'The six smallest dealt plants open the market (3 current, 3 future).',
    russiaShuffledTop:
        'Power plant {p0} goes on top of the deck if it was dealt, then five shuffled cards (the 7th and 8th smallest plants and the top three of the deck).',
    spainHeld:
        'Power plants {p0} are set aside at setup; when Step 2 begins they are placed on top of the deck, smallest on top.',
    ukStep3: 'The Step 3 card is placed third from the bottom of the deck (two plants below it).',
} as const;

type Template = keyof typeof DECK_BUILD_TEMPLATES;

export interface DeckBuildText {
    // How the deck is built when a map says nothing special, for the deck in play.
    standard: string[];
    // This map's departure from it; empty when the map builds its deck normally.
    map: string[];
}

function fill(template: Template, ...values: string[]): string {
    return DECK_BUILD_TEMPLATES[template].replace(/\{p(\d+)\}/g, (_, i) => values[+i]);
}

const isShuffled = (deck: PowerPlantDeck) => deck == 'shuffled' || deck == 'shuffledUnique';
const SINGLE_DECKS: SingleDeck[] = ['standard', 'deck1', 'deck2'];
// The shuffled decks' copy numbering (see plantCopy).
const COPY: Record<SingleDeck, number> = { standard: 0, deck1: 0.1, deck2: 0.2 };
const eachDeck = (numbers: (deck: SingleDeck) => number[]) => ([] as number[]).concat(...SINGLE_DECKS.map(numbers));

// "18, 22, 27" for a single deck; "18, 22, 27 / 15, 16, 26 / 17, 24, 28" (Original
// deck / Deck 1 / Deck 2, by copy) for the shuffled decks.
function plantList(numbers: number[], deck: PowerPlantDeck): string {
    const join = (list: number[]) => list.sort((a, b) => a - b).join(', ');
    if (!isShuffled(deck)) return numbers.join(', ');
    return [0, 1, 2]
        .map((copy) => join(numbers.filter((n) => plantCopy(n) == copy).map(Math.floor)) || '–')
        .join(' / ');
}

function removed(mapName: string, deck: PowerPlantDeck, numPlayers: number, variant: string): string[] {
    let numbers = removedPlants(mapName, deck, numPlayers, variant);
    // India's single decks leave their plant out of the catalogue itself.
    if (mapName == 'India' && !isShuffled(deck)) {
        const india = new Set(plantCatalogue('India', deck).map((p) => p.number));
        numbers = plantCatalogue('', deck)
            .map((p) => p.number)
            .filter((n) => !india.has(n));
    }
    if (!numbers.length) return [];
    return [fill(numbers.length == 1 ? 'removedOne' : 'removedMany', plantList(numbers, deck))];
}

function plugRange(deck: PowerPlantDeck): string {
    const range = (single: PowerPlantDeck) => {
        const plug = plantCatalogue('', single)
            .filter((p) => p.type != PowerPlantType.Step3 && isPlugPlant(p, single))
            .map((p) => p.number);
        return `${plug[0]}-${plug[plug.length - 1]}`;
    };
    return isShuffled(deck) ? SINGLE_DECKS.map(range).join(' / ') : range(deck);
}

// The plants in a single-deck game once the map's removals are made, smallest first.
function dealtPlants(mapName: string, deck: PowerPlantDeck, numPlayers: number, variant: string): PowerPlant[] {
    const gone = removedPlants(mapName, deck, numPlayers, variant);
    return plantCatalogue(mapName, deck).filter((p) => p.type != PowerPlantType.Step3 && !gone.includes(p.number));
}

const numbers = (plants: PowerPlant[]) => plants.map((p) => p.number).join(', ');

// The Original edition's top plant: the shuffled decks use the standard deck's.
function topSentences(top: number[], deck: PowerPlantDeck): string[] {
    if (!top.length) return [fill('originalTopNone')];
    return [fill(isShuffled(deck) ? 'originalTopIfDealt' : 'originalTop', top.join(', '))];
}

function standardText(mapName: string, options: GameOptions, numPlayers: number): string[] {
    const deck = gameDeck(options);
    const intro = !isShuffled(deck)
        ? []
        : [
              fill(
                  deck == 'shuffledUnique'
                      ? 'shuffledUnique'
                      : options.shuffledSample
                      ? 'shuffledSample'
                      : 'shuffledFull'
              ),
              fill('shuffledLegend'),
          ];
    if (options.variant == 'original') {
        // A top plant the map removes (Deck 2's 13 on India and Bremen) leaves no top plant.
        const gone = removedPlants(mapName, deck, numPlayers, 'original');
        const inGame = new Set(dealtPlants(mapName, deck, numPlayers, 'original').map((p) => p.number));
        const top = originalTopPlants('', deck).filter((n) => (isShuffled(deck) ? !gone.includes(n) : inGame.has(n)));
        const market = isShuffled(deck)
            ? [fill('originalMarketShuffled')]
            : (() => {
                  const plants = dealtPlants(mapName, deck, numPlayers, 'original');
                  return [fill('originalMarket', numbers(plants.slice(0, 4)), numbers(plants.slice(4, 8)))];
              })();
        return [
            ...intro,
            ...market,
            top.length ? fill('originalSetAside', top.join(', ')) : fill('originalSetAsideNone'),
            ...topSentences(top, deck),
        ];
    }
    return [
        ...intro,
        fill('plugPlants', plugRange(deck)),
        fill('rechargedMarket'),
        fill('rechargedTop'),
        fill('rechargedRemoval'),
        fill('rechargedRest'),
    ];
}

function many(one: Template, more: Template, plants: number[], deck: PowerPlantDeck): string {
    return fill(plants.length == 1 && !isShuffled(deck) ? one : more, plantList(plants, deck));
}

function mapText(mapName: string, options: GameOptions, numPlayers: number): string[] {
    const deck = gameDeck(options);
    const variant = options.variant ?? 'original';
    const original = variant == 'original';
    const shuffled = isShuffled(deck);
    const gone = removed(mapName, deck, numPlayers, variant);
    switch (mapName) {
        case 'Australia': {
            const mines = (single: SingleDeck) =>
                dealtPlants(mapName, single, numPlayers, variant)
                    .filter((p) => p.type == PowerPlantType.Uranium)
                    .map((p) => p.number + (shuffled ? COPY[single] : 0));
            const all = shuffled ? eachDeck(mines) : mines(deck as SingleDeck);
            return [...gone, fill('australiaMines', plantList(all, deck)), fill('standardSetup')];
        }
        case 'Brazil': {
            if (original) {
                const top = originalTopPlants(mapName, deck);
                return [many('topInOrderOne', 'topInOrderMany', top, deck), fill('brazilOriginalGarbage')];
            }
            const garbage = (single: SingleDeck) =>
                plantCatalogue(mapName, single)
                    .filter((p) => p.type == PowerPlantType.Garbage && !isPlugPlant(p, single))
                    .map((p) => p.number + (shuffled ? COPY[single] : 0));
            const highGarbage = shuffled ? eachDeck(garbage) : garbage(deck as SingleDeck);
            return [
                many('marketAlwaysOne', 'marketAlwaysMany', rechargedMarketPlants(mapName, deck), deck),
                fill('brazilGarbage', plantList(highGarbage, deck)),
            ];
        }
        case 'Bremen':
            return [...gone, fill('noFurtherRemoval'), ...(original ? [] : [fill('bremenMarket')])];
        case 'China':
            return [...gone, fill('chinaOrder'), fill('chinaMarket')];
        case 'Europe':
            return [fill('europeMarket')];
        case 'France': {
            if (original) {
                const top = originalTopPlants(mapName, deck);
                return [...gone, fill(top.length ? 'franceTopInPlace' : 'franceNoTop', top.join(', '))];
            }
            return [
                ...gone,
                many('marketAlwaysOne', 'marketAlwaysMany', rechargedMarketPlants(mapName, deck), deck),
                fill('franceRemoval'),
            ];
        }
        case 'India':
        case 'South Africa':
            return [...gone, fill('standardSetup')];
        case 'Manhattan': {
            const boxed = removedPlants(mapName, deck, numPlayers, variant);
            return [
                fill('manhattanPlug'),
                fill('manhattanRest'),
                ...(boxed.length ? [fill('manhattanBoxed', plantList(boxed, deck))] : []),
            ];
        }
        case 'Northern Europe':
            return [fill(shuffled ? 'northernEuropeShuffled' : 'northernEuropeRegional')];
        case 'Quebec': {
            const ecological = fill(original ? 'quebecEcologicalOriginal' : 'quebecEcological');
            if (shuffled) {
                return [
                    original
                        ? fill('quebecShuffledOriginal', originalTopPlants('', deck).join(', '))
                        : fill('quebecShuffledRecharged'),
                    fill('quebecEcological'),
                ];
            }
            if (original)
                return [many('topInOrderOne', 'topInOrderMany', originalTopPlants(mapName, deck), deck), ecological];
            const market = rechargedMarketPlants(mapName, deck);
            const top = QUEBEC_RECHARGED_TOP_PLANTS[deck as SingleDeck];
            return [
                market.length
                    ? many('marketAlwaysOne', 'marketAlwaysMany', market, deck)
                    : fill('quebecMarketFrom', '3-10, 13'),
                ...(top.length
                    ? [fill(deck == 'standard' ? 'quebecTopBeneath' : 'quebecTopVery', top.join(', '))]
                    : []),
                ecological,
            ];
        }
        case 'Russia': {
            if (!original) return [...gone, fill('russiaRechargedMarket'), fill('russiaRechargedRemoval')];
            const top = originalTopPlants('', deck).join(', ');
            if (shuffled) return [...gone, fill('russiaShuffledMarket'), fill('russiaShuffledTop', top)];
            const plants = dealtPlants(mapName, deck, numPlayers, variant);
            const next = RUSSIA_ORIGINAL_NEXT_PLANTS[deck as SingleDeck];
            return [
                ...gone,
                fill('russiaOriginalMarket', numbers(plants.slice(0, 3)), numbers(plants.slice(3, 6))),
                fill('russiaOriginalTop', top, next.join(', ')),
            ];
        }
        case 'Spain & Portugal': {
            const held = shuffled
                ? eachDeck((single) => SPAIN_STEP_2_PLANTS[single].map((n) => n + COPY[single]))
                : SPAIN_STEP_2_PLANTS[deck as SingleDeck];
            return [fill('spainHeld', plantList(held, deck))];
        }
        case 'UK & Ireland':
            return [fill('ukStep3'), fill('standardSetup')];
        default:
            return [];
    }
}

export function deckBuildText(mapName: string, options: GameOptions, numPlayers: number): DeckBuildText {
    return { standard: standardText(mapName, options, numPlayers), map: mapText(mapName, options, numPlayers) };
}
