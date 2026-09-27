import seedrandom from 'seedrandom';
import { availableMoves } from './available-moves';
import { reconstructState, stripSecret, setup, defaultSetupDeck } from './engine';
import { GameState, PowerPlant, PowerPlantType } from './gamestate';
import { indiaPowerPlants, powerPlants } from './powerPlants';
import { shuffle } from './utils';

/** Unknown cards come from the published catalogue, never the live draw pile. */
export function createAnalysisScenario(
    data: GameState,
    { player, seed }: { player?: number; seed: string }
): GameState {
    const s: GameState = JSON.parse(JSON.stringify(stripSecret(data, player)));
    delete s.powerPlantDeckAfterStep3;
    const rng = seedrandom(seed);
    const name = s.map.name;
    const n = s.players.length;
    let excluded: number[] = [];
    if (name === 'France') excluded = [13];
    if (name === 'Russia') excluded = [6, 14];
    if (name === 'Australia') excluded = [17];
    if (name === 'South Africa') excluded = [7];
    if (name === 'Bremen') excluded = [11, 17, 23, 28, 34, 36, 38, 39, 46, ...(n <= 4 ? [31, 50] : [])];
    if (name === 'Manhattan') excluded = [99, ...(n <= 3 ? [20, 22, 37] : [])];
    if (name === 'China')
        excluded =
            n <= 3 ? [3, 4, 9, 11, 16, 18, 20, 24, 30, 33, 46] : n === 4 ? [3, 4, 11, 18, 24, 33, 46] : [3, 4, 33];
    if (name === 'Spain & Portugal' && s.step === 1) excluded = [18, 22, 27];
    const catalogue = JSON.parse(JSON.stringify(name === 'India' ? indiaPowerPlants : powerPlants)) as PowerPlant[];
    for (const region of new Set(s.map.cities.map((c) => c.region))) {
        for (const replacement of s.map.regionalPowerPlants?.[region] || []) {
            const i = catalogue.findIndex((p) => p.number === replacement.number);
            if (i >= 0) catalogue[i] = { ...replacement };
        }
    }
    const byNumber = (number: number) => catalogue.find((p) => p.number === number)!;
    const seen = new Set([...s.knownPowerPlantDeck, ...s.knownPowerPlantDeckStep3].map((p) => p.number));
    const bottom: number[] = [];
    // Rotation events are public. A later draw consumes that card; Step 3 shuffles
    // the surviving rotations back into the unknown pool.
    const recycled = new Set<number>();
    const recyclePile: number[] = [];
    for (const entry of s.log) {
        if (entry.type !== 'event') continue;
        const setAside = /Setting Power Plant (\d+) aside on the recycle pile/.exec(entry.event);
        if (setAside) recyclePile.push(Number(setAside[1]));
        if (/reshuffling the recycle pile/.test(entry.event)) {
            recyclePile.forEach((number) => recycled.add(number));
            recyclePile.length = 0;
        }
        if (
            /Step 3 will begin|Starting Step 3|reshuffling the recycle pile|Step 2 will begin next phase, discarding/.test(
                entry.event
            )
        ) {
            bottom.forEach((number) => recycled.add(number));
            bottom.length = 0;
        }
        const rotation = /(?:Putting|Sending) Power Plant (\d+) (?:on|to) the bottom of the deck/.exec(entry.event);
        if (rotation) {
            const number = Number(rotation[1]);
            const i = bottom.indexOf(number);
            if (i >= 0) bottom.splice(i, 1);
            bottom.push(number);
            recycled.delete(number);
        }
        const drawn = /Power Plant (\d+) (?:drawn from the deck|discarded\.)/i.exec(entry.event);
        if (drawn) {
            const number = Number(drawn[1]);
            const i = bottom.indexOf(number);
            if (i >= 0) bottom.splice(i, 1);
            recycled.delete(number);
        }
    }
    const unavailable = new Set(
        [
            ...s.actualMarket,
            ...s.futureMarket,
            ...s.players.reduce((all, p) => all.concat(p.powerPlants), [] as PowerPlant[]),
            ...(s.manhattanRecyclePile || []),
        ].map((p) => p.number)
    );
    const fixedBottom = bottom.filter((number) => !unavailable.has(number));
    const pool = catalogue.filter(
        (p) =>
            !excluded.includes(p.number) &&
            !unavailable.has(p.number) &&
            ((!seen.has(p.number) && !(name === 'Manhattan' && s.manhattanDepletion)) || recycled.has(p.number)) &&
            !fixedBottom.includes(p.number)
    );
    // Step 3 can be returned underneath the deck for the Middle East's second pass.
    if (name === 'Middle East' && s.step === 2 && !unavailable.has(99) && !pool.some((p) => p.number === 99))
        pool.push(byNumber(99));
    const step3 = pool.find((p) => p.number === 99);
    let candidates = shuffle(
        pool.filter((p) => p.number !== 99),
        seed
    );
    const count = s.cardsLeft - fixedBottom.length - Number(!!step3);
    const fixedTop: number[] = [];
    const original = s.options.variant === 'original';
    if (original && name !== 'China' && name !== 'Manhattan') {
        const opening =
            name === 'France' ? [11] : name === 'Quebec' ? [13, 18, 22] : name === 'Brazil' ? [13, 14] : [13];
        for (const number of opening) if (!seen.has(number)) fixedTop.push(number);
    }
    if (!original && name === 'Quebec') {
        // The first low plant is followed by the two guaranteed ecological plants.
        for (const number of [18, 22]) if (!seen.has(number)) fixedTop.push(number);
    }
    if (name === 'Spain & Portugal' && s.step === 2) {
        for (const number of [18, 22, 27]) if (!seen.has(number)) fixedTop.push(number);
    }
    const top = fixedTop.map(byNumber).filter((p) => candidates.some((c) => c.number === p.number));
    candidates = candidates.filter((p) => !top.some((t) => t.number === p.number));
    const mandatory = (p: PowerPlant) =>
        (name === 'Brazil' && p.type === PowerPlantType.Garbage && p.number > 14) ||
        (name === 'Quebec' && [PowerPlantType.Wind, PowerPlantType.Nuclear].includes(p.type)) ||
        (name === 'Russia' && original && [10, 11].includes(p.number));
    // A plug-back top card is public information in the recharged edition.
    if (
        (!original || name === 'Manhattan') &&
        name !== 'China' &&
        count > 0 &&
        (top.length === 0 || (name === 'Quebec' && s.nextCardWeak))
    ) {
        candidates = candidates.filter(mandatory).concat(candidates.filter((p) => !mandatory(p)));
        const index = candidates.findIndex(
            (p) =>
                p.number <= 15 === (name === 'Manhattan' && s.knownPowerPlantDeck.length === 8 ? true : s.nextCardWeak)
        );
        if (index >= 0) top.unshift(...candidates.splice(index, 1));
    }
    const select = (cards: PowerPlant[], amount: number) => {
        const required = cards.filter(mandatory);
        return required.concat(cards.filter((p) => !mandatory(p)).slice(0, Math.max(0, amount - required.length)));
    };
    let rest: PowerPlant[];
    if (
        (!original || name === 'Manhattan') &&
        name !== 'China' &&
        !(name === 'Middle East' && s.step > 1) &&
        !(name === 'Manhattan' && s.manhattanDepletion)
    ) {
        const initial =
            name === 'Middle East'
                ? defaultSetupDeck(
                      n,
                      s.options.variant!,
                      seedrandom(seed + ':catalogue-counts'),
                      s.options.useNewRechargedSetup ?? true
                  )
                : setup(n, s.options, seed + ':catalogue-counts');
        const threshold = name === 'India' ? 16 : 15;
        const low = (p: PowerPlant) => p.number <= threshold;
        const initialLow = [...initial.actualMarket, ...initial.futureMarket, ...initial.powerPlantsDeck].filter(
            low
        ).length;
        const seenLow = [...seen].filter((number) => number <= threshold).length;
        const recycledLow = [...recycled].filter((number) => number <= threshold && !unavailable.has(number)).length;
        const lowCount = initialLow - seenLow + recycledLow - top.filter(low).length;
        rest = select(candidates.filter(low), Math.max(0, lowCount)).concat(
            select(
                candidates.filter((p) => !low(p)),
                count - top.length - Math.max(0, lowCount)
            )
        );
        rest = shuffle(rest, seed + ':remaining');
    } else rest = select(candidates, Math.max(0, count - top.length));
    let deck = [...top, ...rest];
    if (name === 'Russia' && s.step < 3) {
        if (original) {
            const remainingWindow = Math.max(0, 6 - Math.max(0, s.knownPowerPlantDeck.length - 6));
            const first = deck.filter((p) => p.number === 13);
            const guaranteed = deck.filter((p) => [10, 11].includes(p.number));
            const others = deck.filter((p) => ![10, 11, 13].includes(p.number));
            deck = first.concat(
                shuffle(
                    guaranteed.concat(
                        others.splice(0, Math.max(0, remainingWindow - first.length - guaranteed.length))
                    ),
                    seed + ':russia'
                ),
                others
            );
        } else deck = deck.filter((p) => p.number <= 15).concat(deck.filter((p) => p.number > 15));
    }
    if (name === 'China') {
        const low = deck.filter((p) => p.number <= 30).sort((a, b) => a.number - b.number);
        const middle = shuffle(
            deck.filter((p) => p.number >= 31 && p.number <= 35).concat(step3 ? [step3] : []),
            seed + ':middle'
        );
        deck = low.concat(
            middle,
            deck.filter((p) => p.number >= 36)
        );
    } else if (step3) {
        deck.splice(name === 'UK & Ireland' ? Math.max(0, deck.length - 2) : deck.length, 0, step3);
    }
    s.powerPlantsDeck = deck.concat(fixedBottom.map(byNumber));
    if (s.powerPlantsDeck.length !== s.cardsLeft)
        throw new Error(
            `Cannot reconstruct public deck: ${name} step ${s.step}, round ${s.round}, needed ${s.cardsLeft}, got ${
                s.powerPlantsDeck.length
            }, bottom ${fixedBottom}, recycled ${[...recycled]}`
        );
    // The visible history permits money accounting without reading hidden balances.
    const publicReplay = reconstructState(s, s.log.length, true);
    s.players.forEach((p, i) => {
        if (p.money < 0) p.money = publicReplay.players[i].money;
        p.isAI = false;
        p.isDropped = false;
        p.lastMove = null;
        delete p.targetCitiesPowered;
        if (s.options.fastBid && i !== player) {
            p.bid =
                s.chosenPowerPlant && !s.currentPlayers.includes(i) && !p.skipAuction && p.money >= s.minimunBid
                    ? Math.min(p.money, s.minimunBid + Math.floor(rng() * Math.max(1, p.money - s.minimunBid + 1)))
                    : 0;
        }
    });
    s.seed = seed;
    s.hiddenLog = [];
    delete s.automation;
    delete s.powerPlantDeckAfterStep3;
    s.newTurn = true;
    s.players.forEach((p) => {
        p.availableMoves = s.currentPlayers.includes(p.id) ? availableMoves(s, p) : null;
    });
    return s;
}
