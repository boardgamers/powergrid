import { expect } from 'chai';
import 'mocha';
import { replay } from '../wrapper';
import { ended, moveAI, reconstructState, setup, stripSecret } from './engine';
import USAOriginal from './fixtures/USAOriginal.json';
import { GameState, MapName } from './gamestate';
import { maps } from './maps';

function expectPublicPosition(actual: GameState, expected: GameState) {
    expect(actual.cardsLeft, 'remaining physical cards').to.equal(expected.cardsLeft);
    expect(actual.powerPlantsDeck.length, 'physical deck size').to.equal(expected.cardsLeft);
    expect(actual.actualMarket).to.deep.equal(expected.actualMarket);
    expect(actual.futureMarket).to.deep.equal(expected.futureMarket);
    expect(actual.step).to.equal(expected.step);
    expect(actual.phase).to.equal(expected.phase);
}

describe('public replay physical deck counts', function () {
    this.timeout(120000);

    for (const [to, count] of [
        [200, 14],
        [400, 4],
    ]) {
        it(`preserves unseen cards at USA move prefix ${to}`, () => {
            const live = replay(USAOriginal as any, { to });
            expect(live.cardsLeft).to.equal(count);
            const publicState = stripSecret(live);
            const before = JSON.stringify(publicState);
            expectPublicPosition(reconstructState(publicState, live.log.length), live);
            expectPublicPosition(reconstructState(publicState), live);
            expectPublicPosition(reconstructState(publicState, live.log.length, true), live);
            expect(JSON.stringify(publicState)).to.equal(before);
        });
    }

    it('recomputes historical counts rather than copying the latest count', () => {
        const latest = replay(USAOriginal as any, { to: 400 });
        const earlier = replay(USAOriginal as any, { to: 200 });
        const publicState = stripSecret(latest);
        for (const expected of [earlier, latest, earlier]) {
            expectPublicPosition(reconstructState(publicState, expected.log.length), expected);
        }
    });

    // Exercise each map's own setup size and lifecycle, including China/Russia's
    // smaller markets, Spain's held-back plants, Middle East's repeated Step 3,
    // and Manhattan's recycle pile and deck depletions.
    for (const map of maps) {
        for (const variant of ['original', 'recharged'] as const) {
            it(`${map.name} ${variant}: live prefixes and historical scrubbing`, () => {
                let live = setup(3, { map: map.name as MapName, variant, fastBid: true }, 'public-counts');
                const positions: GameState[] = [];
                for (let i = 0; i < 1000 && !ended(live); i++) {
                    if (i % 30 === 0) {
                        positions.push(JSON.parse(JSON.stringify(live)));
                        expectPublicPosition(reconstructState(stripSecret(live), live.log.length), live);
                    }
                    live = moveAI(live, live.currentPlayers[0]);
                }
                expect(ended(live), 'bot game finished').to.equal(true);
                positions.push(live);
                const publicState = stripSecret(live);
                const before = JSON.stringify(publicState);
                for (const position of positions.reverse()) {
                    expectPublicPosition(reconstructState(publicState, position.log.length), position);
                }
                expect(JSON.stringify(publicState)).to.equal(before);
            });
        }
    }
});
