import { expect } from 'chai';
import 'mocha';
import { createAnalysisScenario } from './analysis';
import { setup, moveAI, ended } from './engine';
import { maps } from './maps';
import { GameState } from './gamestate';
const clone = (s: GameState): GameState => JSON.parse(JSON.stringify(s));
describe('ongoing analysis scenarios', function () {
    this.timeout(120000);
    for (const n of [2, 3, 4, 6])
        for (const map of maps)
            for (const variant of ['original', 'recharged'] as const) {
                it(`${n}p ${map.name} ${variant} preserves information and remains playable`, () => {
                    let live = setup(n, { map: map.name as any, variant, fastBid: true }, 'source');
                    for (let step = 0; step < 250 && !ended(live); step++) {
                        if (step % 25 === 0) {
                            const before = clone(live);
                            const other = clone(live);
                            other.seed = 'different';
                            other.powerPlantsDeck = [];
                            other.powerPlantDeckAfterStep3 = [];
                            other.hiddenLog = [];
                            delete other.automation;
                            for (const p of other.players)
                                if (p.id !== 0) {
                                    p.money += 500;
                                    p.bid += 100;
                                    p.lastMove = null;
                                }
                            const scenario = createAnalysisScenario(live, { player: 0, seed: 'fake' });
                            expect(scenario).to.deep.equal(createAnalysisScenario(other, { player: 0, seed: 'fake' }));
                            expect(clone(live)).to.deep.equal(before);
                            expect(scenario.players.map((p) => p.money)).to.deep.equal(
                                live.players.map((p) => p.money)
                            );
                            expect(scenario.powerPlantsDeck.length).to.equal(live.cardsLeft);
                            expect(new Set(scenario.powerPlantsDeck.map((p) => p.number)).size).to.equal(
                                scenario.cardsLeft
                            );
                            let branch = scenario;
                            for (let j = 0; j < 40 && !ended(branch); j++)
                                branch = moveAI(branch, branch.currentPlayers[0]);
                        }
                        live = moveAI(live, live.currentPlayers[0]);
                    }
                });
            }
});

describe('analysis information boundaries', () => {
    it('keeps only the requester bid and replaces every secret for a spectator', () => {
        let s = setup(3, { fastBid: true }, 'real-rng');
        s = moveAI(s, s.currentPlayers[0]);
        s = moveAI(s, s.currentPlayers[0]);
        const other = clone(s);
        other.seed = 'private-seed';
        other.powerPlantsDeck = [];
        other.hiddenLog = [];
        other.players.forEach((p) => {
            p.bid += 37;
            p.money += 1000;
            p.lastMove = null;
        });
        expect(createAnalysisScenario(s, { seed: 'simulation' })).to.deep.equal(
            createAnalysisScenario(other, { seed: 'simulation' })
        );
        const own = createAnalysisScenario(s, { player: 0, seed: 'simulation' });
        expect(own.players[0].bid).to.equal(s.players[0].bid);
        expect(own.players[0].money).to.equal(s.players[0].money);
        expect(own.hiddenLog).to.deep.equal([]);
        expect(own.automation).to.equal(undefined);
        expect(createAnalysisScenario(s, { seed: 'another' }).powerPlantsDeck).not.to.deep.equal(own.powerPlantsDeck);
    });
});
