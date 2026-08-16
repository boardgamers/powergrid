import { expect } from 'chai';
import { move as engineMove, MoveName, setup } from 'powergrid-engine';
import type { GameState, Move } from 'powergrid-engine';
import { matchesTurnBuffer, moveMatches, rebaseTurnBuffer, replayTurnBuffer } from '@/util/turn-buffer';

describe('turn-buffer', () => {
    const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value));

    /** Committed 2-player opening state plus the acting player's first two moves. */
    function fixture() {
        const committed = setup(2, {}, 'turn-buffer-test');
        const player = committed.currentPlayers[0];
        const plants = committed.players[player].availableMoves![MoveName.ChoosePowerPlant]!;
        const choose: Move = { name: MoveName.ChoosePowerPlant, data: Math.min(...plants), time: 1000 };
        const bid: Move = { name: MoveName.Bid, data: choose.data as number, time: 2000 };

        return { committed, player, choose, bid };
    }

    it('moveMatches ignores engine annotations but not payload or time stamp', () => {
        const { choose } = fixture();
        const logged = { ...choose, usedPlantDiscount: true } as Move;

        expect(moveMatches(logged, choose)).to.be.true;
        expect(moveMatches(logged, { ...choose, time: 9999 })).to.be.false;
        expect(moveMatches(logged, { ...choose, data: (choose.data as number) + 1 } as Move)).to.be.false;
        expect(moveMatches(logged, undefined)).to.be.false;
    });

    it('matchesTurnBuffer accepts the echo of exactly the current buffer and rejects stale ones', () => {
        const { committed, player, choose } = fixture();
        const tentative = engineMove(clone(committed), choose, player);
        expect(tentative.newTurn).to.be.false;

        // Exact echo of the one-move buffer: valid preview
        expect(matchesTurnBuffer(tentative, committed, [choose], player)).to.be.true;

        // The buffer has since been undone to empty, or grown: the echo is stale
        expect(matchesTurnBuffer(tentative, committed, [], player)).to.be.false;
        expect(matchesTurnBuffer(tentative, committed, [choose, choose], player)).to.be.false;

        // Different buffered move (undo + different action): stale
        const other: Move = { ...choose, time: 1 };
        expect(matchesTurnBuffer(tentative, committed, [other], player)).to.be.false;

        // No committed base yet (fresh viewer): never treat a tentative state as ours
        expect(matchesTurnBuffer(tentative, null, [choose], player)).to.be.false;
    });

    it('rebaseTurnBuffer strips our own committed prefix and empties the buffer on a full echo', () => {
        const { committed, player, choose, bid } = fixture();
        let next: GameState = engineMove(clone(committed), choose, player);
        next = engineMove(next, bid, player);
        expect(next.newTurn, 'the opening bid commits the turn').to.be.true;

        // The whole buffer came back committed: nothing left to replay
        expect(rebaseTurnBuffer(next, committed.log, [choose, bid], player)).to.deep.equal([]);

        // A racing extra move survives the rebase (it is re-sent on the new base)
        const racing: Move = { name: MoveName.Pass, data: true, time: 3000 };
        expect(rebaseTurnBuffer(next, committed.log, [choose, bid, racing], player)).to.deep.equal([racing]);
    });

    it("rebaseTurnBuffer keeps the buffer across another player's commit and scraps it on a mismatch", () => {
        const { committed, player, choose, bid } = fixture();
        const other = 1 - player;
        let next: GameState = engineMove(clone(committed), choose, player);
        next = engineMove(next, bid, player);

        // From the OTHER player's perspective the appended moves are foreign: their
        // (hypothetical) tentative buffer survives untouched, to be replayed on the
        // new base — the simultaneous-Bureaucracy rebase case.
        const foreignBuffer: Move[] = [{ name: MoveName.Pass, data: true, time: 5000 }];
        expect(rebaseTurnBuffer(next, committed.log, foreignBuffer, other)).to.deep.equal(foreignBuffer);

        // But if the appended moves are OURS and do not match the buffer (our turn was
        // superseded, e.g. auto-played after a drop), the buffer is scrapped.
        const mismatched: Move[] = [{ ...choose, time: 42 }];
        expect(rebaseTurnBuffer(next, committed.log, mismatched, player)).to.deep.equal([]);

        // A log that did not grow monotonically (replay scrubbing, reload) also scraps it.
        expect(rebaseTurnBuffer(committed, next.log, foreignBuffer, other)).to.deep.equal([]);
    });

    it('replayTurnBuffer previews the buffer and drops a now-illegal tail gracefully', () => {
        const { committed, player, choose, bid } = fixture();

        const ok = replayTurnBuffer(committed, [choose], player);
        expect(ok.applied).to.deep.equal([choose]);
        expect(ok.state.chosenPowerPlant!.number).to.equal(choose.data);
        expect(ok.state.newTurn).to.be.false;

        // Choosing a second plant mid-auction is illegal: the tail is dropped, the
        // legal prefix survives and still previews
        const truncated = replayTurnBuffer(committed, [choose, choose], player);
        expect(truncated.applied).to.deep.equal([choose]);
        expect(truncated.state.chosenPowerPlant!.number).to.equal(choose.data);

        // The full legal turn previews as committed
        const full = replayTurnBuffer(committed, [choose, bid], player);
        expect(full.applied).to.deep.equal([choose, bid]);
        expect(full.state.newTurn).to.be.true;

        // The input state is never mutated by a preview
        expect(committed.chosenPowerPlant).to.be.undefined;
    });
});
