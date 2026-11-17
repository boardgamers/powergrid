import { expect } from 'chai';
import { cloneDeep } from 'lodash';
import 'mocha';
import * as wrapper from '../wrapper';
import { achievementDefinitions, achievements } from './achievements';
import { createAnalysisScenario } from './analysis';
import { setup } from './engine';
import GermanyRecharged from './fixtures/GermanyRecharged.json';
import USAOriginal from './fixtures/USAOriginal.json';
import { GameState, MapName, Phase, Player, PowerPlantType, Variant } from './gamestate';
import { LogMove } from './log';
import { maps, mapsRecharged } from './maps';

const ids = [
    'grid-champion',
    'head-to-head',
    'full-table',
    'germany-champion',
    'usa-champion',
    'france-champion',
    'japan-champion',
    'brazil-champion',
    'spain-portugal-champion',
    'india-champion',
    'italy-champion',
    'quebec-champion',
    'middle-east-champion',
    'china-champion',
    'benelux-champion',
    'russia-champion',
    'central-europe-champion',
    'baden-wurttemberg-champion',
    'northern-europe-champion',
    'korea-champion',
    'europe-champion',
    'north-america-champion',
    'south-africa-champion',
    'uk-ireland-champion',
    'australia-champion',
    'bremen-champion',
    'manhattan-champion',
    'power-fifteen',
    'power-eighteen',
    'fully-supplied',
    'network-seventeen',
    'network-twenty',
    'cash-reserve',
    'deep-reserves',
    'wind-farm',
    'atomic-power',
];

// Independent explicit expectations: do not derive badge IDs from implementation slugs.
const mapBadges: [MapName, string][] = [
    ['Germany', 'germany-champion'],
    ['USA', 'usa-champion'],
    ['France', 'france-champion'],
    ['Japan', 'japan-champion'],
    ['Brazil', 'brazil-champion'],
    ['Spain & Portugal', 'spain-portugal-champion'],
    ['India', 'india-champion'],
    ['Italy', 'italy-champion'],
    ['Quebec', 'quebec-champion'],
    ['Middle East', 'middle-east-champion'],
    ['China', 'china-champion'],
    ['Benelux', 'benelux-champion'],
    ['Russia', 'russia-champion'],
    ['Central Europe', 'central-europe-champion'],
    ['Baden-Württemberg', 'baden-wurttemberg-champion'],
    ['Northern Europe', 'northern-europe-champion'],
    ['Korea', 'korea-champion'],
    ['Europe', 'europe-champion'],
    ['North America', 'north-america-champion'],
    ['South Africa', 'south-africa-champion'],
    ['UK & Ireland', 'uk-ireland-champion'],
    ['Australia', 'australia-champion'],
    ['Bremen', 'bremen-champion'],
    ['Manhattan', 'manhattan-champion'],
];

// Deliberately synthetic final positions: setup supplies the complete state shape,
// but these boundary tests do not claim their scores came from legal game play.
function finalState(count = 2, map: MapName = 'Germany', variant: Variant = 'original'): GameState {
    const state = setup(count, { map, variant }, 'achievement-boundaries');
    state.phase = Phase.GameEnd;
    state.newTurn = true;
    state.currentPlayers = [];
    state.players.forEach((p) => {
        p.citiesPowered = 0;
        p.money = 0;
        p.cities = [];
        p.powerPlants = [];
    });
    return state;
}

function cities(player: Player, count: number) {
    player.cities = Array.from({ length: count }, (_, i) => ({ name: `Synthetic city ${i}`, position: 0 }));
}

function earned(state: GameState, seat = 0): string[] {
    return achievements(state).find((result) => result.seat === seat)!.earned;
}

function freezeDeep(value: unknown) {
    if (value && typeof value === 'object' && !Object.isFrozen(value)) {
        Object.values(value).forEach(freezeDeep);
        Object.freeze(value);
    }
}

describe('achievements', function () {
    this.timeout(30000);

    it('publishes all 36 stable IDs in a fresh revisioned manifest', () => {
        const manifest = achievementDefinitions();
        expect(manifest.revision).to.equal(3);
        expect(manifest.achievements.map((a) => a.id)).to.deep.equal(ids);
        expect(new Set(ids).size).to.equal(36);
        manifest.achievements.forEach((a) => {
            expect(a.name).to.be.a('string').and.not.equal('');
            expect(a.description).to.be.a('string').and.not.equal('');
        });
        const original = cloneDeep(manifest);
        manifest.achievements[0].name = 'Changed by host';
        manifest.achievements.pop();
        expect(achievementDefinitions()).to.deep.equal(original);
        expect(wrapper.achievementDefinitions()).to.deep.equal(original);
    });

    for (const [variant, runtimeMaps] of [
        ['original', maps],
        ['recharged', mapsRecharged],
    ] as const) {
        it(`${variant} runtime maps exactly match the 24 supported badge names`, () => {
            expect(mapBadges).to.have.length(24);
            expect(new Set(mapBadges.map(([name]) => name)).size).to.equal(24);
            expect(runtimeMaps.map((map) => map.name).sort()).to.deep.equal(mapBadges.map(([name]) => name).sort());
        });

        for (const [map, badge] of mapBadges) {
            for (const count of [2, 6]) {
                it(`awards only the ${map} (${variant}) and ${count}-seat win predicates to the winner`, () => {
                    const state = finalState(count, map, variant);
                    expect(state.map.name).to.equal(map);
                    state.players[1].citiesPowered = 1;
                    const expected = ['grid-champion', count === 2 ? 'head-to-head' : 'full-table', badge];
                    expect(earned(state, 1)).to.deep.equal(expected);
                    state.players.forEach((_, seat) => {
                        if (seat !== 1) expect(earned(state, seat)).to.deep.equal([]);
                    });
                    expect(achievements(state).map((r) => r.outcome)).to.deep.equal(
                        state.players.map((_, seat) => (seat === 1 ? 'win' : 'loss'))
                    );
                    // Requested options may be Random or stale; only the resolved map counts.
                    state.options.map = 'Random';
                    expect(earned(state, 1)).to.deep.equal(expected);
                    state.options.map = map === 'Germany' ? 'USA' : 'Germany';
                    expect(earned(state, 1)).to.deep.equal(expected);
                });
            }
        }
    }

    for (const unsupported of ['Atlantis', 'Random', 'toString', '__proto__']) {
        it(`does not award a map badge for unsupported resolved map ${unsupported}`, () => {
            const state = finalState();
            state.map.name = unsupported as MapName;
            state.players[0].citiesPowered = 1;
            expect(earned(state)).to.deep.equal(['grid-champion', 'head-to-head']);
            expect(earned(state, 1)).to.deep.equal([]);
        });
    }

    for (const [id, field, threshold] of [
        ['power-fifteen', 'power', 15],
        ['power-eighteen', 'power', 18],
        ['network-seventeen', 'cities', 17],
        ['network-twenty', 'cities', 20],
        ['cash-reserve', 'money', 100],
        ['deep-reserves', 'money', 200],
    ] as const) {
        for (const value of [threshold - 1, threshold, threshold + 1]) {
            it(`${id}: ${field} ${value} is ${value >= threshold ? 'eligible' : 'ineligible'}`, () => {
                const state = finalState();
                // A losing player can still earn every non-victory achievement.
                state.players[1].citiesPowered = 100;
                if (field === 'cities') cities(state.players[0], value);
                else if (field === 'power') state.players[0].citiesPowered = value;
                else state.players[0].money = value;
                expect(earned(state).includes(id)).to.equal(value >= threshold);
                expect(achievements(state)[0].outcome).to.equal('loss');
            });
        }
    }

    for (const [network, power, eligible] of [
        [9, 9, false],
        [10, 9, false],
        [10, 10, false],
        [10, 11, false],
        [14, 14, false],
        [15, 14, false],
        [15, 15, true],
        [15, 16, false],
        [16, 15, false],
        [16, 16, true],
        [16, 17, false],
    ] as const) {
        it(`fully supplied requires at least fifteen cities and exact supply (${network}/${power})`, () => {
            const state = finalState();
            cities(state.players[0], network);
            state.players[0].citiesPowered = power;
            expect(earned(state).includes('fully-supplied')).to.equal(eligible);
        });
    }

    for (const [type, id] of [
        [PowerPlantType.Wind, 'wind-farm'],
        [PowerPlantType.Uranium, 'atomic-power'],
    ] as const) {
        for (const capacity of [7, 8, 9]) {
            it(`${id} sums owned capacity at ${capacity}, independent of fuel and powered cities`, () => {
                const state = finalState();
                state.players[0].powerPlants = [
                    { number: 100, type, cost: 2, citiesPowered: 3 },
                    { number: 101, type, cost: 2, citiesPowered: capacity - 3 },
                ];
                expect(earned(state).includes(id)).to.equal(capacity >= 8);
            });
        }
    }

    it('does not count Australian uranium mines or fusion as uranium-fuelled or wind plants', () => {
        const state = finalState(2, 'Australia');
        state.players[0].powerPlants = [{ number: 50, type: PowerPlantType.Uranium, cost: 2, citiesPowered: 8 }];
        expect(earned(state)).not.to.include('atomic-power');
        expect(earned(state).filter((id) => id.endsWith('-champion'))).to.deep.equal([
            'grid-champion',
            'australia-champion',
        ]);
        for (const map of ['Australia', 'Germany'] as MapName[]) {
            const fusion = finalState(2, map);
            fusion.players[0].powerPlants = [{ number: 50, type: PowerPlantType.Nuclear, cost: 0, citiesPowered: 8 }];
            expect(earned(fusion)).not.to.include('atomic-power');
            expect(earned(fusion)).not.to.include('wind-farm');
        }
    });

    it('uses power, then money, then cities for ranks, with exact co-winners', () => {
        const state = finalState(6);
        const scores = [
            [18, 100, 20],
            [18, 100, 20],
            [18, 100, 19],
            [18, 99, 21],
            [17, 200, 22],
            [16, 300, 23],
        ];
        scores.forEach(([power, money, network], seat) => {
            state.players[seat].citiesPowered = power;
            state.players[seat].money = money;
            cities(state.players[seat], network);
        });
        expect(wrapper.rankings(state)).to.deep.equal([1, 1, 3, 4, 5, 6]);
        expect(achievements(state).map((r) => r.outcome)).to.deep.equal(['win', 'win', 'loss', 'loss', 'loss', 'loss']);
        expect(earned(state, 0)).to.include('grid-champion');
        expect(earned(state, 1)).to.include('grid-champion');
        expect(earned(state, 2)).not.to.include('grid-champion');
    });

    for (const flag of ['isAI', 'isDropped'] as const) {
        it(`omits ${flag} seats without removing them from competition or renumbering seats`, () => {
            const state = finalState(3);
            state.players[0][flag] = true;
            state.players[0].citiesPowered = 20;
            expect(achievements(state).map((r) => [r.seat, r.outcome])).to.deep.equal([
                [1, 'loss'],
                [2, 'loss'],
            ]);
            state.players[1].citiesPowered = 20;
            expect(achievements(state).map((r) => [r.seat, r.outcome])).to.deep.equal([
                [1, 'win'],
                [2, 'loss'],
            ]);
        });
    }

    for (const win of [false, true]) {
        it(`reports an explicit ${win ? 'win' : 'loss'} for the only human against bots`, () => {
            const state = finalState(6);
            state.players.forEach((p, seat) => {
                p.isAI = seat !== 3;
                p.citiesPowered = 10;
            });
            state.players[3].citiesPowered = win ? 11 : 9;
            const result = achievements(state);
            expect(result).to.have.length(1);
            expect(result[0].seat).to.equal(3);
            expect(result[0].outcome).to.equal(win ? 'win' : 'loss');
            expect(result[0].earned.includes('full-table')).to.equal(win);
        });
    }

    it('excludes unfinished, tentative, hypothetical and analysis states', () => {
        expect(achievements(setup(2, {}, 'unfinished'))).to.deep.equal([]);
        const state = finalState();
        state.newTurn = false;
        expect(achievements(state)).to.deep.equal([]);
        state.newTurn = true;
        state.analysisMoney = 'hypothetical';
        expect(achievements(state)).to.deep.equal([]);
        delete state.analysisMoney;
        state.achievementAnalysis = true;
        expect(achievements(state)).to.deep.equal([]);
        const singleton = finalState();
        singleton.players.splice(1);
        expect(achievements(singleton)).to.deep.equal([]);
    });

    it('marks both analysis constructors, even without hypothetical money, and excludes their final states', () => {
        const source = setup(3, {}, 'analysis-achievements');
        const branches = [
            wrapper.createAnalysis(source, { to: source.log.length, sourceEnded: false }),
            wrapper.createAnalysisScenario(source, { seed: 'interactive' }),
            createAnalysisScenario(source, { seed: 'simulation' }),
        ];
        for (const branch of branches) {
            expect(branch.achievementAnalysis).to.equal(true);
            delete branch.analysisMoney;
            branch.phase = Phase.GameEnd;
            branch.newTurn = true;
            expect(achievements(branch)).to.deep.equal([]);
        }
        expect(source.achievementAnalysis).to.equal(undefined);
    });

    it('preserves analysis exclusion through replay and marks analysis moves on legacy branches', async () => {
        const source = setup(3, {}, 'legacy-analysis-achievements');
        const branch = wrapper.createAnalysis(source, { to: source.log.length, sourceEnded: false });
        expect(wrapper.replay(branch).achievementAnalysis).to.equal(true);
        const legacy = await wrapper.analysisMove(source, [], 0);
        expect(legacy.achievementAnalysis).to.equal(true);
        legacy.phase = Phase.GameEnd;
        legacy.newTurn = true;
        expect(achievements(legacy)).to.deep.equal([]);
        expect(source.achievementAnalysis).to.equal(undefined);
    });

    it('is pure on deeply frozen input and returns fresh arrays and records', () => {
        const state = finalState();
        state.players[0].money = 200;
        const before = cloneDeep(state);
        freezeDeep(state);
        const first = achievements(state);
        const second = achievements(state);
        expect(state).to.deep.equal(before);
        expect(first).to.deep.equal(second);
        expect(first).not.to.equal(second);
        first.forEach((result, seat) => {
            expect(result).not.to.equal(second[seat]);
            expect(result.earned).not.to.equal(second[seat].earned);
        });
        first[0].earned.push('host-mutation');
        first[0].outcome = 'loss';
        expect(achievements(state)).to.deep.equal(second);
        expect(wrapper.achievements(state)).to.deep.equal(second);
    });

    for (const [name, fixture, expectedRanks] of [
        ['GermanyRecharged', GermanyRecharged, [4, 2, 3, 1]],
        ['USAOriginal', USAOriginal, [1, 3, 2]],
    ] as const) {
        it(`replays authentic ${name} and awards only after its legal final transition`, async () => {
            const original = cloneDeep(fixture) as unknown as GameState;
            const replayed = wrapper.replay(cloneDeep(original));
            expect(wrapper.ended(replayed)).to.equal(true);
            expect(wrapper.rankings(replayed)).to.deep.equal(expectedRanks);
            expect(achievements(replayed)).to.deep.equal(achievements(original));
            expect(achievements(replayed).map((r) => r.outcome)).to.deep.equal(
                expectedRanks.map((rank) => (rank === 1 ? 'win' : 'loss'))
            );
            const lastMoveIndex = original.log.reduce((last, item, i) => (item.type === 'move' ? i : last), -1);
            const beforeEnd = wrapper.replay(cloneDeep(original), { to: lastMoveIndex });
            expect(wrapper.ended(beforeEnd)).to.equal(false);
            expect(achievements(beforeEnd)).to.deep.equal([]);
            const last = original.log[lastMoveIndex] as LogMove;
            const finished = await wrapper.move(beforeEnd, last.move, last.player);
            expect(wrapper.ended(finished)).to.equal(true);
            expect(finished.newTurn).to.equal(true);
            expect(achievements(finished)).to.deep.equal(achievements(replayed));
        });
    }
});
