import { expect } from 'chai';
import 'mocha';
import * as wrapper from '../wrapper';
import { addPowerPlant, getPowerPlant, move, reconstructState, setup } from './engine';
import RussiaStep3 from './fixtures/RussiaStep3.json';
import { GameOptions, GameState, MapName, Phase } from './gamestate';
import { Move, MoveName } from './move';

const pass: Move = { name: MoveName.Pass, data: true };
function lastPlayerIn(phase: Phase, map: MapName = 'Germany'): GameState {
    const G = setup(3, { map, variant: 'original' }, 'step-messages');
    G.round = 3;
    G.phase = phase;
    G.currentPlayers = [0];
    G.players.forEach((p) => {
        p.passed = p.id !== 0;
        p.skipAuction = p.id !== 0;
        p.availableMoves = { [MoveName.Pass]: [true] };
    });
    return G;
}
function takeMessages(G: GameState, expected: number[]) {
    expect(wrapper.messages(G).messages).to.deep.equal(expected.map((step) => `Starting Step ${step}.`));
    expect(wrapper.messages(G).messages, 'announcements are consumed once').to.deep.equal([]);
    for (const step of expected) {
        expect(
            G.log.some((entry) => entry.type === 'event' && entry.event.includes(`Step ${step}`)),
            `Step ${step} also appears in the log`
        ).to.equal(true);
    }
}

describe('step announcements', () => {
    it('announces Step 2 when the last builder finishes, not when the threshold is reached', async () => {
        const G = lastPlayerIn(Phase.Building);
        G.players[0].cities = [{ name: G.map.cities[0].name, position: 0 }];
        G.citiesToStep2 = 1;
        takeMessages(G, []);
        const result = await wrapper.move(G, pass, 0);
        expect(result.step).to.equal(2);
        expect(wrapper.toSave(result)).to.equal(result);
        takeMessages(result, [2]);
    });

    it('waits for the auction to finish before announcing Step 3', async () => {
        const G = lastPlayerIn(Phase.Auction);
        G.step = 2;
        G.actualMarket.shift();
        G.powerPlantsDeck.unshift(getPowerPlant(99));
        addPowerPlant(G);
        expect(G.step).to.equal(2);
        takeMessages(G, []);
        const result = await wrapper.move(G, pass, 0);
        expect(result.step).to.equal(3);
        takeMessages(result, [3]);
    });

    for (const phase of [Phase.Building, Phase.Bureaucracy]) {
        it(`logs and announces Step 3 at the end of ${phase}`, async () => {
            const G = lastPlayerIn(phase);
            G.step = 2;
            G.actualMarket.shift();
            G.powerPlantsDeck.unshift(getPowerPlant(99));
            addPowerPlant(G);
            expect(G.step).to.equal(2);
            takeMessages(G, []);
            const result = await wrapper.move(G, pass, 0);
            expect(result.step).to.equal(3);
            takeMessages(result, [3]);
            expect(
                result.log.filter((entry) => entry.type === 'event' && entry.event === 'Starting Step 3.')
            ).to.have.lengthOf(1);
        });
    }

    it('announces both UK & Ireland steps when Step 3 is drawn before the city threshold', async () => {
        const G = lastPlayerIn(Phase.Building, 'UK & Ireland');
        G.actualMarket.shift();
        G.powerPlantsDeck.unshift(getPowerPlant(99));
        addPowerPlant(G);
        expect(G.step).to.equal(2);
        const result = await wrapper.move(G, pass, 0);
        expect(result.step).to.equal(3);
        takeMessages(result, [2, 3]);
    });

    it('announces the Middle East first deck depletion as Step 2', () => {
        const G = lastPlayerIn(Phase.Building, 'Middle East');
        G.actualMarket.shift();
        G.powerPlantsDeck.unshift(getPowerPlant(99));
        addPowerPlant(G);
        expect(G.step).to.equal(2);
        takeMessages(G, [2]);
    });

    it('announces China Step 3 as soon as its card is drawn', () => {
        const G = lastPlayerIn(Phase.Auction, 'China');
        G.step = 2;
        G.powerPlantsDeck.unshift(getPowerPlant(99));
        addPowerPlant(G);
        expect(G.step).to.equal(3);
        takeMessages(G, [3]);
    });

    it('does not repeat Step 3 in subsequent rounds', async () => {
        const G = lastPlayerIn(Phase.Bureaucracy);
        G.step = 3;
        G.actualMarket.push(...G.futureMarket.splice(0));
        const result = await wrapper.move(G, pass, 0);
        takeMessages(result, []);
    });

    it('does not announce steps on Manhattan, which stays in Step 1', async () => {
        const G = lastPlayerIn(Phase.Building, 'Manhattan');
        G.futureMarket = [];
        const result = await wrapper.move(G, pass, 0);
        expect(result.step).to.equal(1);
        takeMessages(result, []);
    });

    for (const fixture of [RussiaStep3]) {
        it(`announces both steps once in a full ${fixture.options.map} game without reposting on replay`, () => {
            let G = setup(fixture.players.length, fixture.options as GameOptions, fixture.seed);
            const announcements: string[] = [];
            for (const entry of fixture.log) {
                if (entry.type === 'move') {
                    G = move(G, entry.move as Move, entry.player!);
                    announcements.push(...wrapper.messages(G).messages);
                }
            }
            expect(announcements).to.deep.equal(['Starting Step 2.', 'Starting Step 3.']);
            takeMessages(wrapper.replay(G), []);
            takeMessages(reconstructState(G), []);
        });
    }
});
