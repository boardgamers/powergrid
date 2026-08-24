import {
    matchesTurnBuffer,
    moveMatches,
    rebaseTurnBuffer,
    replayTurnBuffer,
    shouldAdoptLogState,
} from '@/util/turn-buffer';
import { expect } from 'chai';
import type { GameState, Move } from 'powergrid-engine';
import { move as engineMove, moveAI, MoveName, Phase, setup } from 'powergrid-engine';

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

    it('shouldAdoptLogState only adopts a state while it is tentative', () => {
        const { committed, player, choose } = fixture();
        const tentative = engineMove(clone(committed), choose, player);

        // The one thing the gamelog state channel exists for
        expect(shouldAdoptLogState(tentative), "a tentative state is the acting player's own").to.be.true;

        // A committed state on this channel may have come from the plain log fetch,
        // which is not logged-in: stripSecret blanks every player's availableMoves when
        // the player index is -1, so adopting it kills the board until the game is
        // re-entered. Refetch instead.
        expect(shouldAdoptLogState(committed), 'a committed state is refetched').to.be.false;
        const blanked = {
            ...clone(committed),
            players: committed.players.map((pl) => ({ ...pl, availableMoves: {} })),
        };
        expect(shouldAdoptLogState(blanked as GameState), 'especially a blanked one').to.be.false;

        // Engine >= 2.0.1 omits state entirely when it cannot attribute it
        expect(shouldAdoptLogState(undefined), 'no state at all').to.be.false;
        expect(shouldAdoptLogState(null), 'null state').to.be.false;
    });

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

        // A racing extra move is scrapped when the commit ends our turn — the bid
        // handed the auction to the other player, so nothing of ours can replay on
        // the new base. (Previously it was kept and only died in the replay's
        // illegal-move error path.)
        const racing: Move = { name: MoveName.Pass, data: true, time: 3000 };
        expect(next.currentPlayers).to.not.include(player);
        expect(rebaseTurnBuffer(next, committed.log, [choose, bid, racing], player)).to.deep.equal([]);
    });

    it('rebaseTurnBuffer scraps a leftover fastBid bid whose effect committed to the hidden log', () => {
        const committed = setup(2, { fastBid: true }, 'turn-buffer-fastbid');
        const player = committed.currentPlayers[0];
        const plants = committed.players[player].availableMoves![MoveName.ChoosePowerPlant]!;
        const choose: Move = { name: MoveName.ChoosePowerPlant, data: Math.min(...plants), time: 1000 };
        const bid: Move = { name: MoveName.Bid, data: choose.data as number, time: 2000 };

        let next: GameState = engineMove(clone(committed), choose, player);
        expect(next.newTurn, 'the chooser is still on the clock to bid').to.be.false;
        next = engineMove(next, bid, player);
        expect(next.newTurn, 'a fastBid bid commits immediately').to.be.true;

        // The bid went to the HIDDEN log: the committed echo extends the visible log
        // by the choose alone. The leftover [bid] is nonetheless already reflected in
        // the state — the mover left currentPlayers — so the rebase scraps it cleanly
        // instead of leaving it to be rejected (noisily) by the replay.
        expect(next.log.length).to.equal(committed.log.length + 1);
        expect(next.currentPlayers).to.not.include(player);
        expect(rebaseTurnBuffer(next, committed.log, [choose, bid], player)).to.deep.equal([]);
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

    // The reason the viewer previews a move locally BEFORE sending it (Game.vue
    // sendMove). These two tests describe the bug that motivated it: eric-hu's #131,
    // "Wrong argument for the command BuyResource" at the end of a game.
    it('previewing a move advances availableMoves, which is what disables the next illegal click', () => {
        const { committed, player, choose } = fixture();

        // The viewer used to judge every click against the last state the SERVER sent.
        // A click made before the reply landed was therefore built from a stale list.
        expect(
            committed.players[player].availableMoves![MoveName.ChoosePowerPlant],
            'the stale list still offers a plant to choose'
        ).to.include(choose.data as number);

        // Sending both is what the platform rejects: it replays the WHOLE buffer.
        expect(() => {
            let s = engineMove(clone(committed), choose, player);
            engineMove(s, { ...choose, time: 2000 } as Move, player);
        }, 'the platform replays the buffer and throws').to.throw();

        // Previewing the buffer locally moves the board on, so the second click is
        // never offered — the illegal buffer cannot be built in the first place.
        const { state } = replayTurnBuffer(committed, [choose], player);
        expect(state.players[player].availableMoves![MoveName.ChoosePowerPlant]).to.be.undefined;
    });

    it('a preview after every buy stops a resource click going past storage capacity', () => {
        // Drive a real game to a seat that can buy resources.
        let G: GameState = setup(4, {}, 'turn-buffer-resources');
        for (let i = 0; i < 4000; i++) {
            const seat = G.players.findIndex((p) => p.availableMoves);
            if (seat < 0) break;
            if (G.phase === Phase.Resources && G.players[seat].availableMoves![MoveName.BuyResource]) {
                const stale = G.players[seat].availableMoves![MoveName.BuyResource]!;
                const target = stale[0];

                // How many of that resource fit? Buy until the engine stops offering it.
                let previewed: GameState = clone(G);
                const buffer: Move[] = [];
                for (let n = 0; n < 40; n++) {
                    // No optional chaining in this file: webpack 4 parses the unit-test
                    // bundle and rejects it (same note as util/turn-buffer.ts).
                    const moves = previewed.players[seat].availableMoves;
                    const fresh = moves ? moves[MoveName.BuyResource] : undefined;
                    if (!fresh || !fresh.some((m) => JSON.stringify(m) === JSON.stringify(target))) break;
                    const buy: Move = { name: MoveName.BuyResource, data: target, time: 1000 + n };
                    buffer.push(buy);
                    previewed = replayTurnBuffer(G, buffer, seat).state;
                }
                expect(buffer.length, 'the seat can buy at least one cube').to.be.greaterThan(0);

                // WITHOUT a preview the cube stays clickable, so one more click is
                // buffered and the platform rejects the whole turn.
                const oneTooMany = [...buffer, { name: MoveName.BuyResource, data: target, time: 9999 } as Move];
                expect(() => {
                    let s: GameState = clone(G);
                    for (const m of oneTooMany) s = engineMove(s, m, seat);
                }, 'this is the state eric-hu got stuck in').to.throw(/BuyResource/);

                // WITH a preview, the extra click is never offered, and even if one
                // races in the replay truncates it rather than sending it on.
                expect(replayTurnBuffer(G, oneTooMany, seat).applied).to.deep.equal(buffer);
                return;
            }
            G = moveAI(G, seat);
        }
        expect.fail('never reached a seat that could buy resources');
    });
});
