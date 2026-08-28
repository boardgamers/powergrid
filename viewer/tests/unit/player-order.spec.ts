import { playerOrderForDisplay } from '@/util/player-order';
import { expect } from 'chai';
import type { GameState } from 'powergrid-engine';
import { moveAI, Phase, setup } from 'powergrid-engine';

/**
 * #141. coyotte508 reported that toggling "adjust player order" on and off lands on
 * inconsistent states. The cause is that the viewer read the order by REVERSING the
 * game state's array in place, so every read edited the thing it was reading.
 *
 * These tests are about that property, not about the arrow of the order: reading a
 * value must be repeatable, and must leave the board alone.
 */
describe('player-order', () => {
    const realRandom = Math.random;
    const pinDice = (dice: number) => {
        let s = dice >>> 0;
        Math.random = () => {
            s = (s * 1664525 + 1013904223) >>> 0;
            return s / 4294967296;
        };
    };
    afterEach(() => {
        Math.random = realRandom;
    });

    /** A real mid-game state, in `phase`, whose playerOrder is genuinely permuted. */
    function stateIn(phase: Phase, dice = 1): GameState {
        pinDice(dice);
        let G: GameState = setup(4, { map: 'Germany', variant: 'recharged' } as never, '5');
        for (let i = 0; i < 40000; i++) {
            // Round 2+ so the order has been re-derived from cities at least once.
            if (G.round >= 3 && G.phase === phase) return G;
            const idx = G.players.findIndex((p) => p.availableMoves);
            if (idx < 0) break;
            G = moveAI(G, idx);
        }
        throw new Error(`never reached ${phase}`);
    }

    it('reading the order does not edit the game state', () => {
        const G = stateIn(Phase.Resources);
        const before = [...G.playerOrder];

        playerOrderForDisplay(G, true);

        // PlayerOrder.vue draws the goldenrod 1-6 track straight off G.playerOrder, in
        // a $nextTick that runs AFTER this getter has been evaluated for the render.
        // A getter that mutates therefore prints the track backwards on the board.
        expect(G.playerOrder, 'the display read rewrote the turn order').to.deep.equal(before);
    });

    it('reading the order twice gives the same answer', () => {
        const G = stateIn(Phase.Resources);

        // Copy the first read. A getter that returns the state's own array hands back
        // the SAME object twice, so comparing the two references compares a value to
        // itself and passes no matter how wrong it is -- this test did exactly that
        // until the copy was added.
        const first = [...playerOrderForDisplay(G, true)];
        const second = playerOrderForDisplay(G, true);

        expect(second, 'two reads of one unchanged state disagreed').to.deep.equal(first);
    });

    it('survives the toggle coyotte508 screenshotted: on, off, on', () => {
        const G = stateIn(Phase.Resources);

        const on = [...playerOrderForDisplay(G, true)];
        playerOrderForDisplay(G, false);
        const onAgain = playerOrderForDisplay(G, true);

        expect(onAgain, 'the setting means something different on its second activation').to.deep.equal(on);
    });

    it('stacks the boards in the order each phase actually plays', () => {
        const auction = stateIn(Phase.Auction);
        expect(playerOrderForDisplay(auction, true), 'the auction runs down the turn order').to.deep.equal(
            auction.playerOrder
        );

        const resources = stateIn(Phase.Resources);
        expect(playerOrderForDisplay(resources, true), 'resources run back up it').to.deep.equal(
            [...resources.playerOrder].reverse()
        );

        const building = stateIn(Phase.Building);
        expect(playerOrderForDisplay(building, true), 'so does building').to.deep.equal(
            [...building.playerOrder].reverse()
        );
    });

    it('with the preference off, the boards keep table order', () => {
        const G = stateIn(Phase.Resources);
        expect(playerOrderForDisplay(G, false)).to.deep.equal([0, 1, 2, 3]);
    });
});
