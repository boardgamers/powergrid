import type { TutorialOptions, TutorialStep } from '@boardgamers/protocol/tutorial';
import type { GameState, Move } from 'powergrid-engine';
import { availableMoves, move as engineMove, setup } from 'powergrid-engine';
import { Phase, PowerPlantType, ResourceType } from 'powergrid-engine/src/gamestate';
import { map as germany } from 'powergrid-engine/src/maps/germany';
import { MoveName } from 'powergrid-engine/src/move';
import { powerPlants as plants } from 'powergrid-engine/src/powerPlants';

export type Action = { kind: 'move'; move: Move } | { kind: 'watch' } | { kind: 'answer'; answer: string };
export interface LessonState {
    game: GameState;
    answer?: string;
    watched: number;
}
export interface Choice {
    label: string;
    action: Action;
}
export interface Lesson extends Omit<TutorialOptions<LessonState, Action>, 'move'> {
    title: string;
    description: string;
    move(state: LessonState, action: Action, frame?: (game: GameState) => void): LessonState;
    choices(state: LessonState, step: string): Choice[];
}
const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value));
const pass: Move = { name: MoveName.Pass, data: true };
const plant = (number: number) => copy(plants.find((p) => p.number === number)!);
const bid = (data: number): Move => ({ name: MoveName.Bid, data });
const choose = (data: number): Move => ({ name: MoveName.ChoosePowerPlant, data });
const you = (s: LessonState) => s.game.players[0];
const has = (s: LessonState, number: number) => you(s).powerPlants.some((p) => p.number === number);
const inPhase = (phase: Phase) => (s: LessonState) => s.game.phase === phase;

function activate(game: GameState, phase: Phase, seats: number[]) {
    game.phase = phase;
    game.currentPlayers = seats;
    game.players.forEach((p) => {
        p.availableMoves = seats.includes(p.id) ? availableMoves(game, p) : null;
    });
}
function base(): GameState {
    // Three adjacent regions, including the Ruhr's inexpensive starting connections.
    const map = copy(germany);
    map.cities = map.cities.filter((c) => ['green', 'red', 'brown'].includes(c.region));
    const names = new Set(map.cities.map((c) => c.name));
    map.connections = map.connections.filter((c) => c.nodes.every((n) => names.has(n)));
    const game = setup(3, { map: 'Germany', variant: 'original', showMoney: true }, 'powergrid-tutorial-1');
    // Keep the engine's computed layout while fixing the regions used by the lessons.
    game.map.cities = map.cities;
    game.map.connections = map.connections;
    game.players.forEach((p, i) => {
        p.name = ['You', 'Ada', 'Leo'][i];
    });
    return game;
}
function own(game: GameState, seat: number, numbers: number[]) {
    const p = game.players[seat];
    p.powerPlants = numbers.map(plant);
    p.powerPlantsNotUsed = [...numbers];
    for (const type of ['coal', 'oil', 'garbage', 'uranium', 'hybrid'] as const) p[`${type}Capacity`] = 0;
    for (const card of p.powerPlants) {
        const key = (
            {
                [PowerPlantType.Coal]: 'coal',
                [PowerPlantType.Oil]: 'oil',
                [PowerPlantType.Garbage]: 'garbage',
                [PowerPlantType.Uranium]: 'uranium',
                [PowerPlantType.Hybrid]: 'hybrid',
            } as const
        )[card.type];
        if (key) p[`${key}Capacity`] += card.cost * 2;
    }
    game.actualMarket = game.actualMarket.filter((p) => !numbers.includes(p.number));
    game.futureMarket = game.futureMarket.filter((p) => !numbers.includes(p.number));
    game.powerPlantsDeck = game.powerPlantsDeck.filter((p) => !numbers.includes(p.number));
}
function market(game: GameState, numbers: number[]) {
    game.actualMarket = numbers.slice(0, game.step === 3 ? 6 : 4).map(plant);
    game.futureMarket = game.step === 3 ? [] : numbers.slice(4).map(plant);
    const held = game.players.flatMap((p) => p.powerPlants.map((p) => p.number));
    game.powerPlantsDeck = plants.filter((p) => !numbers.includes(p.number) && !held.includes(p.number)).map(copy);
    game.cardsLeft = game.powerPlantsDeck.length;
}
function cities(game: GameState, seat: number, names: string[]) {
    game.players[seat].cities = names.map((name) => ({
        name,
        position: game.players.filter((p) => p.id !== seat && p.cities.some((c) => c.name === name)).length,
    }));
    game.players[seat].housesLeft = 22 - names.length;
}
function fuel(game: GameState, seat: number, resource: ResourceType, count: number) {
    const key = `${resource}Left` as const;
    const needed = count - game.players[seat][key];
    const fromSupply = Math.min(game[`${resource}Supply`], needed);
    game[`${resource}Supply`] -= fromSupply;
    game[`${resource}Market`] -= needed - fromSupply;
    game.players[seat][key] = count;
}
function state(game: GameState): LessonState {
    return { game, watched: 0 };
}
function midgame(phase: Phase): GameState {
    const game = base();
    game.round = 4;
    game.playerOrder = [2, 1, 0];
    own(game, 0, [4]);
    own(game, 1, [3]);
    own(game, 2, [5]);
    market(game, [6, 7, 8, 9, 10, 11, 12, 13]);
    activate(game, phase, [0]);
    return game;
}
function run(game: GameState, move: Move, seat: number, frame?: (game: GameState) => void) {
    engineMove(game, copy(move), seat);
    frame?.(copy(game));
}
function finishOtherAuctions(game: GameState, frame?: (game: GameState) => void) {
    for (let guard = 0; game.phase === Phase.Auction && guard < 30; guard++) {
        const seat = game.currentPlayers[0];
        if (seat === 0) throw Error('The learner still has an auction decision.');
        const moves = game.players[seat].availableMoves!;
        const next = moves.ChoosePowerPlant
            ? choose(moves.ChoosePowerPlant[0])
            : moves.Bid && !game.currentBid
            ? bid(moves.Bid[0])
            : pass;
        run(game, next, seat, frame);
    }
    if (game.phase === Phase.Auction) throw Error('Auction script did not finish.');
}
function finishIncome(game: GameState, frame?: (game: GameState) => void) {
    for (let guard = 0; game.phase === Phase.Bureaucracy && guard < 20; guard++) {
        const seat = game.currentPlayers[0];
        const usable = game.players[seat].availableMoves?.UsePowerPlant?.[0];
        run(game, usable ? { name: MoveName.UsePowerPlant, data: usable } : pass, seat, frame);
    }
    if (game.phase === Phase.Bureaucracy) throw Error('Income script did not finish.');
}
function apply(id: string, original: LessonState, action: Action, frame?: (game: GameState) => void): LessonState {
    const next = copy(original);
    next.answer = undefined;
    const game = next.game;
    if (action.kind === 'answer') next.answer = action.answer;
    else if (action.kind === 'watch') {
        next.watched++;
        if (id === 'auctions') finishOtherAuctions(game, frame);
        else if (id === 'income') finishIncome(game, frame);
        else if (id === 'steps') {
            finishIncome(game, frame);
            // The engine handles the Step 3 card drawn during market upkeep.
        }
    } else {
        run(game, action.move, 0, frame);
        if (id === 'auctions' && action.move.name === MoveName.Bid) {
            if (action.move.data === 4) {
                run(game, bid(5), 1, frame);
                run(game, pass, 2, frame);
            } else if (action.move.data === 6) run(game, pass, 1, frame);
        }
        if (['network', 'steps', 'final-round'].includes(id) && action.move.name === MoveName.Pass) {
            while (game.phase === Phase.Building && !game.currentPlayers.includes(0))
                run(game, pass, game.currentPlayers[0], frame);
        }
    }
    return next;
}

type Step = TutorialStep<LessonState, Action>;
function actionStep(
    id: string,
    title: string,
    text: string | ((s: LessonState) => string),
    accepts: (a: Action, s: LessonState) => boolean,
    complete: (s: LessonState) => boolean,
    target?: string
): Step {
    return {
        id,
        title,
        text,
        target,
        complete,
        validateMove: (s, a) =>
            accepts(a, s) ? undefined : 'Follow this step first. ' + (typeof text === 'string' ? text : text(s)),
    };
}
const moveIs = (name: MoveName, data?: unknown) => (a: Action) =>
    a.kind === 'move' &&
    a.move.name === name &&
    (data === undefined || JSON.stringify(a.move.data) === JSON.stringify(data));
function quiz(id: string, title: string, text: string, answer: string, success: string): Step {
    return {
        id,
        title,
        text,
        complete: (s) => s.answer === answer,
        validateMove: (_s, a) => (a.kind === 'answer' && a.answer === answer ? undefined : 'Not quite. ' + text),
        success,
    };
}
function answers(...labels: string[]): Choice[] {
    return labels.map((label) => ({ label, action: { kind: 'answer', answer: label } }));
}
const watch = (label: string): Choice[] => [{ label, action: { kind: 'watch' } }];
const watchIs = (a: Action) => a.kind === 'watch';
function chapter(
    id: string,
    title: string,
    description: string,
    initialState: () => LessonState,
    steps: Step[],
    completion: { title: string; text: string },
    choices: Lesson['choices'] = () => []
): Lesson {
    return {
        game: 'powergrid',
        id,
        title,
        description,
        version: 1,
        initialState,
        steps,
        completion,
        move: (s, a, frame) => apply(id, s, a, frame),
        choices,
    };
}

export const lessons: Lesson[] = [
    chapter(
        'auctions',
        'Your first power plant',
        'Read a plant, start an auction and decide how far to bid.',
        () => state(base()),
        [
            {
                id: 'welcome',
                title: 'Build a network that you can power',
                text: 'Buy power plants, buy their fuel, connect cities, then earn income by supplying electricity. At the end, the player who can power the most cities wins. These lessons use Germany and the classic rules with two scripted opponents.',
            },
            actionStep(
                'choose',
                'Choose plant 4',
                'Only the four plants in the current market are for sale. Plant 4 burns 2 coal to power 1 city. Its large number is its minimum opening price, not its output. Click plant 4.',
                moveIs(MoveName.ChoosePowerPlant, 4),
                (s) => s.game.chosenPowerPlant?.number === 4,
                'plants'
            ),
            actionStep(
                'open',
                'Open at $4',
                'Confirm an opening bid of $4 using the auction calculator. Keep some cash for fuel and connections.',
                moveIs(MoveName.Bid, 4),
                (s) => s.game.currentBid === 5,
                'plants'
            ),
            actionStep(
                'raise',
                'Ada offers $5',
                'Leo has passed. Raise to $6. Once you pass in an auction, you cannot rejoin that auction, but you may compete for a later plant.',
                moveIs(MoveName.Bid, 6),
                (s) => has(s, 4),
                'plants'
            ),
            actionStep(
                'others',
                'One plant per round',
                'You paid $6 and have $44 left. You cannot buy another plant this round. Watch Ada and Leo buy theirs. Plants are drawn and sorted again after each purchase.',
                watchIs,
                inPhase(Phase.Resources)
            ),
        ],
        {
            title: 'Ready to buy fuel',
            text: 'A higher plant number does not necessarily mean better value. Compare its fuel cost and output, then leave money for the rest of the round. In Recharged games, the discount token sets the cheapest market plant’s opening bid to $1, regardless of its printed number.',
        },
        (_s, step) => (step === 'others' ? watch('Watch the remaining auctions') : [])
    ),

    chapter(
        'resources',
        'Fuel and rising prices',
        'Buy coal, see prices rise and learn your storage limit.',
        () => {
            const game = midgame(Phase.Resources);
            game.coalSupply += game.coalMarket - 20;
            game.coalMarket = 20;
            activate(game, Phase.Resources, [0]);
            return state(game);
        },
        [
            {
                id: 'order',
                title: 'Last in player order buys first',
                text: 'Fuel is bought in reverse player order. You are last on the order track, so you buy first. Plant 4 needs 2 coal each time it runs and can store 4, enough for two rounds.',
            },
            actionStep(
                'coal-one',
                'Buy one coal',
                'Click one coal in the resource market. Each token has its own price, and the cheapest available token is bought first.',
                (a) =>
                    a.kind === 'move' &&
                    a.move.name === MoveName.BuyResource &&
                    a.move.data.resource === ResourceType.Coal,
                (s) => you(s).coalLeft === 1,
                'resources'
            ),
            actionStep(
                'coal-two',
                'Enough for this round',
                'Buy a second coal. You now have the 2 coal needed to run plant 4 once.',
                (a) =>
                    a.kind === 'move' &&
                    a.move.name === MoveName.BuyResource &&
                    a.move.data.resource === ResourceType.Coal,
                (s) => you(s).coalLeft === 2,
                'resources'
            ),
            quiz(
                'price',
                'What does the next coal cost?',
                'The two $2 coal are gone. Look at the next occupied market space. What will one more coal cost?',
                '$3',
                'Correct! As cheap tokens disappear, later buyers pay more.'
            ),
            actionStep(
                'reserve',
                'Store fuel for next round',
                'Buy 2 more coal, one at a time. They cost $3 each. This fills your plant’s storage: 4 coal in total.',
                (a) =>
                    a.kind === 'move' &&
                    a.move.name === MoveName.BuyResource &&
                    a.move.data.resource === ResourceType.Coal,
                (s) => you(s).coalLeft === 4,
                'resources'
            ),
            actionStep(
                'done',
                'Finish buying',
                'You spent $10 and have $40 left. You cannot store a fifth coal or buy fuel that none of your plants can use. Click Done to let Ada buy.',
                moveIs(MoveName.Pass),
                (s) => !s.game.currentPlayers.includes(0),
                'turn'
            ),
        ],
        {
            title: 'Fuel is a shared market',
            text: 'Stored fuel carries over. Used fuel returns to the supply, and the market is refilled after income. Hybrid plants can burn a mix of coal and oil, with one shared storage limit. Wind plants need no fuel.',
        },
        (_s, step) => (step === 'price' ? answers('$1', '$2', '$3') : [])
    ),

    chapter(
        'network',
        'Connect your cities',
        'Pay for a city and the cheapest route from your network.',
        () => {
            const game = midgame(Phase.Building);
            own(game, 0, [8]);
            market(game, [6, 7, 9, 10, 11, 12, 13, 14]);
            activate(game, Phase.Building, [0]);
            return state(game);
        },
        [
            actionStep(
                'first',
                'Start in Essen',
                'Your first city costs $10, with no connection fee. Click Essen on the map. In Step 1, each city has room for only one player.',
                (a) => a.kind === 'move' && a.move.name === MoveName.Build && a.move.data.name === 'Essen',
                (s) => you(s).cities.length === 1,
                'destination'
            ),
            actionStep(
                'second',
                'A free connection',
                'Connect Duisburg. The route from Essen costs $0, so you pay only the $10 city fee. You may connect several cities in one turn.',
                (a) => a.kind === 'move' && a.move.name === MoveName.Build && a.move.data.name === 'Duisburg',
                (s) => you(s).cities.length === 2,
                'destination'
            ),
            quiz(
                'route',
                'What would Düsseldorf cost?',
                'Düsseldorf has an empty $10 space. The cheapest connection from your network costs $2. What is the total?',
                '$12',
                'Correct! $10 for the city plus $2 for the connection.'
            ),
            actionStep(
                'third',
                'Connect Düsseldorf',
                'Click Düsseldorf and pay $12. The game finds the cheapest route from any city you already own. Routes may pass through other cities without buying a house there.',
                (a) => a.kind === 'move' && a.move.name === MoveName.Build && a.move.data.name === 'Dusseldorf',
                (s) => you(s).cities.length === 3,
                'destination'
            ),
            actionStep(
                'done',
                'Keep some cash',
                'You have $18 left. Plant 8 can power only 2 of your 3 cities, so expansion alone will not increase this round’s income. Click Done to finish building.',
                moveIs(MoveName.Pass),
                inPhase(Phase.Bureaucracy),
                'turn'
            ),
        ],
        {
            title: 'Your network is growing',
            text: 'Building also follows reverse player order. Plan both your routes and your generating capacity. You can leave cities unpowered; they remain in your network.',
        },
        (_s, step) => (step === 'route' ? answers('$2', '$10', '$12') : [])
    ),

    chapter(
        'income',
        'Power cities and earn income',
        'Run your plants, collect income and understand the next turn order.',
        () => {
            const game = midgame(Phase.Bureaucracy);
            own(game, 0, [4, 13]);
            market(game, [6, 7, 8, 9, 10, 11, 12, 14]);
            cities(game, 0, ['Essen', 'Duisburg', 'Dusseldorf']);
            cities(game, 1, ['Hamburg', 'Kiel']);
            cities(game, 2, ['Hannover']);
            fuel(game, 0, ResourceType.Coal, 2);
            fuel(game, 1, ResourceType.Oil, 2);
            fuel(game, 2, ResourceType.Coal, 2);
            game.players[0].money = 18;
            activate(game, Phase.Bureaucracy, [0, 1, 2]);
            return state(game);
        },
        [
            actionStep(
                'coal',
                'Run your coal plant',
                'Click your plant 4. It consumes 2 coal and supplies 1 city. Each plant can run once per round; you cannot pay extra fuel to run it twice.',
                (a) => a.kind === 'move' && a.move.name === MoveName.UsePowerPlant && a.move.data.powerPlant === 4,
                (s) => !you(s).powerPlantsNotUsed.includes(4),
                'players'
            ),
            actionStep(
                'wind',
                'Free wind power',
                'Click plant 13. It needs no fuel and supplies 1 more city, bringing your total to 2.',
                (a) => a.kind === 'move' && a.move.name === MoveName.UsePowerPlant && a.move.data.powerPlant === 13,
                (s) => you(s).citiesPowered === 2,
                'players'
            ),
            actionStep(
                'pay',
                'Collect $33',
                'The $ amounts on the city track show total income: 0 powered cities earns $10, 1 earns $22, 2 earn $33, and 3 earn $44. Your houses mark 3 cities built, but you powered only 2, so collect $33. Click Done.',
                moveIs(MoveName.Pass),
                (s) => you(s).money === 51,
                'turn'
            ),
            actionStep(
                'others',
                'Finish the round',
                'Watch Ada and Leo run their plants and collect income. The resource market then refills and the plant market changes.',
                watchIs,
                (s) => s.game.round === 5
            ),
            quiz(
                'order',
                'Who chooses an auction first?',
                'You have 3 cities, Ada has 2 and Leo has 1. Most cities goes first; a tie is broken by the highest-numbered plant. Who goes first next round?',
                'You',
                'Correct! You choose an auction first, but buy fuel and build last.'
            ),
        ],
        {
            title: 'Keep the whole round in mind',
            text: 'A large network puts you early in the auction order and late in resource buying and building. Sometimes waiting to expand saves money. Even powering no cities normally earns $10.',
        },
        (_s, step) =>
            step === 'others'
                ? watch('Watch income and market upkeep')
                : step === 'order'
                ? answers('You', 'Ada', 'Leo')
                : []
    ),

    chapter(
        'upgrades',
        'Replace an old power plant',
        'Upgrade your output while respecting the three-plant limit.',
        () => {
            const game = midgame(Phase.Auction);
            own(game, 0, [4, 8, 13]);
            market(game, [25, 26, 27, 28, 29, 30, 31, 32]);
            game.playerOrder = [0, 1, 2];
            game.players[1].skipAuction = game.players[2].skipAuction = true;
            activate(game, Phase.Auction, [0]);
            return state(game);
        },
        [
            actionStep(
                'buy',
                'Buy plant 25',
                'Ada and Leo have already bought this round. Choose plant 25 and confirm the $25 purchase. It uses 2 coal to power 5 cities, compared with just 1 city for plant 4.',
                moveIs(MoveName.ChoosePowerPlant, 25),
                (s) => has(s, 25),
                'plants'
            ),
            actionStep(
                'discard',
                'Keep your best three',
                'In a three-player game you may keep 3 plants. Click your old plant 4 to discard it. You get no refund. Stored fuel can move to compatible plants, but excess fuel must be discarded.',
                moveIs(MoveName.DiscardPowerPlant, 4),
                (s) => !has(s, 4),
                'players'
            ),
        ],
        {
            title: 'More output, less fuel',
            text: 'Your remaining plants can supply up to 8 cities: 2 + 1 + 5. You still need enough cities and fuel to use that output. The two-player classic game allows 4 plants instead of 3.',
        }
    ),

    chapter(
        'steps',
        'When the game opens up',
        'Trigger Step 2 and see how Step 3 changes cities and the plant market.',
        () => {
            const game = midgame(Phase.Building);
            cities(game, 0, ['Essen', 'Duisburg', 'Dusseldorf', 'Dortmund', 'Münster', 'Osnabrück']);
            cities(game, 1, ['Hamburg', 'Kiel']);
            cities(game, 2, ['Hannover']);
            market(game, [18, 19, 20, 21, 22, 23, 24, 25]);
            game.powerPlantsDeck = [plant(26), plant(99)];
            game.cardsLeft = game.powerPlantsDeck.length;
            activate(game, Phase.Building, [0]);
            return state(game);
        },
        [
            actionStep(
                'seventh',
                'Connect your seventh city',
                'Rounds repeat; Steps are larger changes during the game. Here Step 2 will start once someone has 7 cities, after everyone finishes building. Connect Kassel.',
                (a) => a.kind === 'move' && a.move.name === MoveName.Build && a.move.data.name === 'Kassel',
                (s) => you(s).cities.length === 7,
                'destination'
            ),
            actionStep(
                'finish',
                'Finish the building phase',
                'Click Done. Ada and Leo will also finish, and the game will enter Step 2.',
                moveIs(MoveName.Pass),
                (s) => s.game.step === 2,
                'turn'
            ),
            quiz(
                'second-space',
                'Now two players fit in a city',
                'In Step 2, a second player may build in an occupied city. That second space costs $15, plus the connection. An empty city still costs $10. Can you build a second house of your own in Essen?',
                'No',
                'Correct! Each player may have only one house in each city.'
            ),
            actionStep(
                'step-three',
                'The Step 3 card',
                'This example is near the end of the plant deck. Finish income and watch the Step 3 card appear during market upkeep.',
                watchIs,
                (s) => s.game.step === 3
            ),
            quiz(
                'market',
                'All six are available',
                'Step 3 allows a third player in each city for $20 plus connections. The plant market has 6 cards and no future market. How many of those plants can be chosen for auction?',
                'All 6',
                'Correct! All six market plants are available in Step 3.'
            ),
        ],
        {
            title: 'Watch the Step, not just the round',
            text: 'Step 2 opens second city spaces; Step 3 opens third spaces and the whole plant market. Resource refill rates also change. Other maps and player counts may use different thresholds.',
        },
        (_s, step) =>
            step === 'second-space'
                ? answers('Yes', 'No')
                : step === 'step-three'
                ? watch('Finish the round')
                : step === 'market'
                ? answers('Only 4', 'All 6')
                : []
    ),

    chapter(
        'final-round',
        'Who actually wins?',
        'Trigger the end and compare cities built with cities powered.',
        () => {
            const game = midgame(Phase.Building);
            game.step = 3;
            game.round = 10;
            own(game, 0, [20, 29, 32]);
            own(game, 1, [25, 36, 44]);
            own(game, 2, [13, 18, 22]);
            market(game, [30, 31, 33, 34, 35, 37]);
            const names = game.map.cities.map((c) => c.name);
            cities(game, 0, names.slice(0, 16));
            cities(game, 1, names.slice(0, 16));
            cities(game, 2, names.slice(0, 15));
            fuel(game, 0, ResourceType.Coal, 4);
            fuel(game, 0, ResourceType.Oil, 3);
            fuel(game, 1, ResourceType.Coal, 5);
            game.players[0].money = 100;
            activate(game, Phase.Building, [0]);
            return state(game);
        },
        [
            {
                id: 'ending',
                title: 'One last building phase',
                text: 'On this three-player map, reaching 17 cities triggers the end after everyone finishes building. You and Ada each have 16 cities. You can power 15; Ada can power 16. Building another house will not improve your plants.',
            },
            actionStep(
                'trigger',
                'Connect a seventeenth city',
                'Connect any affordable city you do not own. The other players still get to finish this building phase.',
                (a) => a.kind === 'move' && a.move.name === MoveName.Build,
                (s) => you(s).cities.length === 17,
                'map'
            ),
            quiz(
                'predict',
                'Who is ahead?',
                'You now have 17 cities but can power only 15. Ada has 16 cities and enough plants and fuel to power all 16. Who will win if nobody builds further?',
                'Ada',
                'Correct! Powered cities decide the winner, not houses placed.'
            ),
            actionStep(
                'finish',
                'See the result',
                'Click Done. Ada and Leo will finish without building. The game checks everyone’s plants and stored fuel automatically.',
                moveIs(MoveName.Pass),
                inPhase(Phase.GameEnd),
                'turn'
            ),
        ],
        {
            title: 'Power wins the game',
            text: 'Ada wins with 16 powered cities, ahead of your 15. Remaining cash breaks a tie in powered cities. There is no ordinary income payment at the end, so buy the fuel you need before the final building phase.',
        },
        (_s, step) => (step === 'predict' ? answers('You', 'Ada', 'Leo') : [])
    ),
];
