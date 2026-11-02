import { expect } from 'chai';
import { init, moveAI, replay } from '../wrapper';
import { reconstructState, setup } from './engine';
import { GameState } from './gamestate';

const json = (G: GameState) => JSON.parse(JSON.stringify(G));

// Plays the first moves with the AI, so replays have resource purchases to repeat.
function playAI(G: GameState, moves: number): GameState {
    for (let i = 0; i < moves && G.currentPlayers.length > 0; i++) G = moveAI(G, G.currentPlayers[0]);
    return G;
}

describe('starting resources by variant', () => {
    for (const map of ['France', 'Brazil'] as const) {
        it(`fills garbage on spaces 6-8 for ${map} Recharged and 7-8 for ${map} Original`, async () => {
            for (let players = 2; players <= 6; players++) {
                const recharged = await init(players, [], { map, variant: 'recharged' }, 'garbage');
                expect(recharged.garbageMarket).to.equal(9);
                expect(recharged.garbageSupply).to.equal(15);
                expect(recharged.options.rechargedStartingResources).to.equal(true);

                const original = await init(players, [], { map, variant: 'original' }, 'garbage');
                expect(original.garbageMarket).to.equal(6);
                expect(original.garbageSupply).to.equal(18);
                expect(original.options).to.not.have.property('rechargedStartingResources');
            }
        });

        it(`replays ${map} Recharged games created before the fix with their original market`, () => {
            // A game created before the fix: 6 garbage, and no flag in its stored options.
            const legacy = playAI(
                setup(4, { map, variant: 'recharged', rechargedStartingResources: false }, 'old'),
                60
            );
            expect(legacy.options).to.not.have.property('rechargedStartingResources');
            expect(json(replay(legacy))).to.deep.equal(json(legacy));
            expect(reconstructState(legacy, 0).garbageMarket).to.equal(6);

            const current = playAI(setup(4, { map, variant: 'recharged' }, 'new'), 60);
            expect(json(replay(current))).to.deep.equal(json(current));
            expect(reconstructState(current, 0).garbageMarket).to.equal(9);
        });
    }

    it('leaves the options of maps with a single starting market unchanged', async () => {
        for (const map of ['Spain & Portugal', 'Germany', 'Italy', 'UK & Ireland'] as const) {
            const G = await init(4, [], { map, variant: 'recharged' }, 'garbage');
            expect(G.options).to.not.have.property('rechargedStartingResources');
        }
    });
});
