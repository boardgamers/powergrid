import seedrandom from 'seedrandom';
import { availableMoves } from './available-moves';
import {
    originalTopPlants,
    QUEBEC_RECHARGED_TOP_PLANTS,
    removedPlants,
    RUSSIA_ORIGINAL_NEXT_PLANTS,
    SPAIN_STEP_2_PLANTS,
} from './deckChanges';
import { defaultSetupDeck, reconstructState, setup, stripSecret } from './engine';
import { GameState, PowerPlant, PowerPlantType } from './gamestate';
import {
    gameDeck,
    isEcological,
    isPlugPlant,
    labelledPlant,
    lastPlugPlant,
    plantCatalogue,
    PLANT_LABEL_PATTERN,
} from './powerPlants';
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
    const powerPlantDeck = gameDeck(s.options);
    // Spain & Portugal's held-back plants return at Step 2; Manhattan boxes its Step 3 card.
    let excluded = removedPlants(name, powerPlantDeck, n, s.options.variant!);
    if (name === 'Spain & Portugal' && s.step !== 1) excluded = [];
    if (name === 'Manhattan') excluded = [99, ...excluded];
    const catalogue = JSON.parse(JSON.stringify(plantCatalogue(name, powerPlantDeck))) as PowerPlant[];
    for (const region of new Set(s.regionDraft ? [] : s.map.cities.map((c) => c.region))) {
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
        const setAside = new RegExp(`Setting Power Plant ${PLANT_LABEL_PATTERN} aside on the recycle pile`).exec(
            entry.event
        );
        if (setAside) recyclePile.push(labelledPlant(setAside[1], setAside[2]));
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
        const rotation = new RegExp(
            `(?:Putting|Sending) Power Plant ${PLANT_LABEL_PATTERN} (?:on|to) the bottom of the deck`
        ).exec(entry.event);
        if (rotation) {
            const number = labelledPlant(rotation[1], rotation[2]);
            const i = bottom.indexOf(number);
            if (i >= 0) bottom.splice(i, 1);
            bottom.push(number);
            recycled.delete(number);
        }
        const drawn = new RegExp(`Power Plant ${PLANT_LABEL_PATTERN} (?:drawn from the deck|discarded\\.)`, 'i').exec(
            entry.event
        );
        if (drawn) {
            const number = labelledPlant(drawn[1], drawn[2]);
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
    let pool = catalogue.filter(
        (p) =>
            !excluded.includes(p.number) &&
            !unavailable.has(p.number) &&
            ((!seen.has(p.number) && !(name === 'Manhattan' && s.manhattanDepletion)) || recycled.has(p.number)) &&
            !fixedBottom.includes(p.number)
    );
    // One per number: a copy already known rules out the number's other copies, and
    // each still-unknown number is in the game exactly once.
    if (powerPlantDeck === 'shuffledUnique') {
        const known = new Set([...seen, ...unavailable, ...fixedBottom]);
        const knownPrinted = new Set([...known].map((number) => Math.floor(number)));
        const unknown = (p: PowerPlant) => p.number !== 99 && !known.has(p.number);
        pool = pool.filter((p) => !unknown(p) || !knownPrinted.has(Math.floor(p.number)));
        const copies = new Map<number, PowerPlant[]>();
        for (const p of pool.filter(unknown)) {
            copies.set(Math.floor(p.number), [...(copies.get(Math.floor(p.number)) ?? []), p]);
        }
        const pick = seedrandom(seed + ':unique');
        const chosen = new Set([...copies.values()].map((options) => options[Math.floor(pick() * options.length)]));
        pool = pool.filter((p) => !unknown(p) || chosen.has(p));
    }
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
        for (const number of originalTopPlants(name, powerPlantDeck)) if (!seen.has(number)) fixedTop.push(number);
    }
    if (!original && name === 'Quebec') {
        // The first low plant is followed by the two guaranteed ecological plants.
        for (const number of QUEBEC_RECHARGED_TOP_PLANTS[powerPlantDeck]) if (!seen.has(number)) fixedTop.push(number);
    }
    if (name === 'Spain & Portugal' && s.step === 2) {
        for (const number of SPAIN_STEP_2_PLANTS[powerPlantDeck]) if (!seen.has(number)) fixedTop.push(number);
    }
    const top = fixedTop.map(byNumber).filter((p) => candidates.some((c) => c.number === p.number));
    candidates = candidates.filter((p) => !top.some((t) => t.number === p.number));
    const mandatory = (p: PowerPlant) =>
        (name === 'Brazil' && p.type === PowerPlantType.Garbage && p.number > lastPlugPlant(powerPlantDeck)) ||
        // Games without the stored ruling built their Québec deck protecting fusion too.
        (name === 'Quebec' && isEcological(p, s.options.fusionEcological ?? true)) ||
        (name === 'Russia' && original && RUSSIA_ORIGINAL_NEXT_PLANTS[powerPlantDeck].includes(p.number));
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
                isPlugPlant(p, powerPlantDeck) ===
                (name === 'Manhattan' && s.knownPowerPlantDeck.length === 8 ? true : s.nextCardWeak)
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
                      s.options.useNewRechargedSetup ?? true,
                      powerPlantDeck,
                      name
                  )
                : setup(n, s.options, seed + ':catalogue-counts');
        const low = (p: { number: number }) => (name === 'India' ? p.number <= 16 : isPlugPlant(p, powerPlantDeck));
        const initialLow = [...initial.actualMarket, ...initial.futureMarket, ...initial.powerPlantsDeck].filter(
            low
        ).length;
        const seenLow = [...seen].filter((number) => low({ number })).length;
        const recycledLow = [...recycled].filter((number) => low({ number }) && !unavailable.has(number)).length;
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
            const topNumber = originalTopPlants(name, powerPlantDeck)[0];
            const nextNumbers = RUSSIA_ORIGINAL_NEXT_PLANTS[powerPlantDeck];
            const first = deck.filter((p) => p.number === topNumber);
            const guaranteed = deck.filter((p) => nextNumbers.includes(p.number));
            const others = deck.filter((p) => p.number !== topNumber && !nextNumbers.includes(p.number));
            deck = first.concat(
                shuffle(
                    guaranteed.concat(
                        others.splice(0, Math.max(0, remainingWindow - first.length - guaranteed.length))
                    ),
                    seed + ':russia'
                ),
                others
            );
        } else {
            const lastPlug = lastPlugPlant(powerPlantDeck);
            deck = deck.filter((p) => p.number <= lastPlug).concat(deck.filter((p) => p.number > lastPlug));
        }
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
