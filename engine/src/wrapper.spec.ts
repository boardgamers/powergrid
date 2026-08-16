import { expect } from 'chai';
import { cloneDeep } from 'lodash';
import 'mocha';
import * as wrapper from '../wrapper';
import { setup } from './engine';
import { GameState, Phase, PowerPlantType, ResourceType } from './gamestate';
import { Move, MoveName } from './move';

const pass: Move = { name: MoveName.Pass, data: true };

const json = (value: unknown) => JSON.parse(JSON.stringify(value));

describe('wrapper (tentative turns)', () => {
    /**
     * Simulates the platform: `saved` only ever advances when `toSave` returns the
     * state (committed); tentative states are discarded, like the game server does.
     */
    class Platform {
        saved: GameState;
        logLengths: number[] = [];

        constructor(players = 2, seed = 'wrapper-test', options = {}) {
            this.saved = setup(players, options, seed);
            this.logLengths.push(wrapper.logLength(this.saved));
        }

        /** Replay a turn buffer from the saved state, persist only if committed. */
        async send(moves: Move | Move[], player: number): Promise<{ result: GameState; saved: boolean }> {
            const result = await wrapper.move(cloneDeep(this.saved), moves, player);
            const toSave = wrapper.toSave(result);

            if (toSave) {
                this.saved = toSave;
                this.logLengths.push(wrapper.logLength(this.saved));
            }

            return { result, saved: !!toSave };
        }

        available(player: number) {
            return this.saved.players[player].availableMoves!;
        }
    }

    /** The cheapest plant the player may put up for auction in the saved state. */
    function cheapestChoosable(platform: Platform, player: number): Move {
        const options = platform.available(player)[MoveName.ChoosePowerPlant]!;
        return { name: MoveName.ChoosePowerPlant, data: Math.min(...options) };
    }

    /**
     * The minimum opening bid after choosing a plant: its number (original variant;
     * the chooser is still the current player and must open the bidding).
     */
    function openingBid(choose: Move): Move {
        return { name: MoveName.Bid, data: choose.data as number };
    }

    /**
     * Scripted 2-player round-1 auction: A (the starting player) chooses the cheapest
     * plant and opens with the minimum bid; B passes the bidding (making A the winner)
     * and then buys the now-cheapest plant uncontested, which ends the auction phase.
     */
    async function playRound1Auction(platform: Platform): Promise<{ A: number; B: number }> {
        const A = platform.saved.currentPlayers[0];
        const B = 1 - A;

        expect(platform.saved.phase).to.equal(Phase.Auction);

        const choose = cheapestChoosable(platform, A);
        await platform.send([choose, openingBid(choose)], A);
        await platform.send([pass], B);
        await platform.send([cheapestChoosable(platform, B)], B);

        expect(platform.saved.phase).to.equal(Phase.Resources);

        return { A, B };
    }

    /**
     * Buys `count` cubes of `resource` for `player` (each buy tentative, growing the
     * buffer), then passes — one committed Resources turn.
     */
    async function buyResourcesAndPass(platform: Platform, player: number, resource: ResourceType, count: number) {
        const buffer: Move[] = [];
        for (let i = 0; i < count; i++) {
            const buyable = platform.available(player)[MoveName.BuyResource]!;
            const entry = buyable.find((option) => option.resource === resource);
            expect(entry, `player ${player} must be offered ${resource}`).to.not.be.undefined;
            buffer.push({ name: MoveName.BuyResource, data: entry! });

            const mid = await platform.send([...buffer], player);
            expect(mid.saved, 'a resource buy is still undoable').to.be.false;
        }

        const full = await platform.send([...buffer, pass], player);
        expect(full.saved, 'passing commits the Resources turn').to.be.true;
    }

    /** Drives a 2-player game to the (simultaneous) Bureaucracy phase. */
    async function playToBureaucracy(platform: Platform): Promise<{ A: number; B: number }> {
        const { A, B } = await playRound1Auction(platform);

        // Resources: reverse player order; each player stocks their single plant
        // (a hybrid plant burns coal here; wind/nuclear plants need nothing).
        for (const player of [...platform.saved.playerOrder].reverse()) {
            const plant = platform.saved.players[player].powerPlants[0];
            const wanted =
                plant.type === PowerPlantType.Coal || plant.type === PowerPlantType.Hybrid
                    ? ResourceType.Coal
                    : plant.type === PowerPlantType.Oil
                    ? ResourceType.Oil
                    : plant.type === PowerPlantType.Garbage
                    ? ResourceType.Garbage
                    : plant.type === PowerPlantType.Uranium
                    ? ResourceType.Uranium
                    : null;
            const buyable = platform.available(player)[MoveName.BuyResource] ?? [];
            const entry = wanted && buyable.find((option) => option.resource === wanted);
            if (entry) {
                await buyResourcesAndPass(platform, player, entry.resource, plant.cost);
            } else {
                await platform.send([pass], player);
            }
        }

        // Building: everyone passes (players may power zero cities for the base income).
        expect(platform.saved.phase).to.equal(Phase.Building);
        for (const player of [...platform.saved.playerOrder].reverse()) {
            await platform.send([pass], player);
        }

        expect(platform.saved.phase).to.equal(Phase.Bureaucracy);
        expect(platform.saved.currentPlayers).to.have.members([A, B]);

        return { A, B };
    }

    it('should keep mid-turn states tentative and commit when the turn completes', async () => {
        const platform = new Platform();
        const A = platform.saved.currentPlayers[0];

        // Mid-turn move: still undoable, must not be saved...
        const choose = cheapestChoosable(platform, A);
        const mid = await platform.send([choose], A);
        expect(mid.saved).to.be.false;
        expect(mid.result.newTurn).to.be.false;
        expect(wrapper.toSave(mid.result)).to.be.undefined;
        // ...but the tentative state did apply the move for the player's preview
        expect(mid.result.chosenPowerPlant?.number).to.equal(choose.data);

        // The tentative state was NOT persisted
        expect(platform.saved.chosenPowerPlant).to.be.undefined;
        expect(wrapper.logLength(platform.saved)).to.equal(1);

        // Completed turn: the full buffer replays from the saved state and commits
        // (after the opening bid, the other player is up)
        const full = await platform.send([choose, openingBid(choose)], A);
        expect(full.saved).to.be.true;
        expect(full.result.newTurn).to.be.true;
        expect(platform.saved.chosenPowerPlant?.number).to.equal(choose.data);
        expect(platform.saved.currentPlayers).to.not.include(A);
    });

    it('should accept a bare move object as a one-element buffer', async () => {
        const platform = new Platform();
        const A = platform.saved.currentPlayers[0];
        const choose = cheapestChoosable(platform, A);

        const fromObject = await wrapper.move(cloneDeep(platform.saved), choose, A);
        const fromArray = await wrapper.move(cloneDeep(platform.saved), [choose], A);

        expect(json(fromObject)).to.deep.equal(json(fromArray));
    });

    it('should not save an empty buffer and not grant it any progress', async () => {
        const platform = new Platform();
        const A = platform.saved.currentPlayers[0];

        const result = await wrapper.move(cloneDeep(platform.saved), [], A);
        expect(wrapper.toSave(result)).to.be.undefined;
        expect(wrapper.logLength(result)).to.equal(wrapper.logLength(platform.saved));
    });

    it('should make undo-by-truncation equivalent to never having made the popped move', async () => {
        const platform = new Platform();
        const A = platform.saved.currentPlayers[0];
        const options = platform.available(A)[MoveName.ChoosePowerPlant]!;
        const chooseFirst: Move = { name: MoveName.ChoosePowerPlant, data: options[0] };
        const chooseSecond: Move = { name: MoveName.ChoosePowerPlant, data: options[1] };

        // A tentative detour ([chooseFirst], then undone to an empty buffer — nothing
        // is ever sent for the undo itself) leaves no trace: the next turn replays
        // from the same saved state as if the detour never happened.
        const detour = await platform.send([chooseFirst], A);
        expect(detour.saved).to.be.false;

        const afterUndo = await platform.send([chooseSecond, openingBid(chooseSecond)], A);
        expect(afterUndo.saved).to.be.true;

        const control = new Platform();
        await control.send([chooseSecond, openingBid(chooseSecond)], A);
        expect(json(afterUndo.result)).to.deep.equal(json(control.saved));
    });

    it('should replay a truncated buffer identically to a fresh shorter buffer', async () => {
        const platform = new Platform(2, 'wrapper-test-truncate');
        const { B } = await playRound1Auction(platform);
        void B;

        // Resources phase: the current player buys two cubes, then "undoes" one — the
        // truncated buffer must reproduce the one-cube state exactly.
        const player = platform.saved.currentPlayers[0];
        const first = platform.available(player)[MoveName.BuyResource]![0];
        const buy1: Move = { name: MoveName.BuyResource, data: first };

        const oneCube = await platform.send([buy1], player);
        expect(oneCube.saved).to.be.false;

        const second = oneCube.result.players[player].availableMoves![MoveName.BuyResource]![0];
        const buy2: Move = { name: MoveName.BuyResource, data: second };

        const twoCubes = await platform.send([buy1, buy2], player);
        expect(twoCubes.saved).to.be.false;

        const truncated = await platform.send([buy1], player);
        expect(json(truncated.result)).to.deep.equal(json(oneCube.result));
    });

    it('should reject a malformed buffer without leaking anything half-applied', async () => {
        const platform = new Platform();
        const A = platform.saved.currentPlayers[0];
        const choose = cheapestChoosable(platform, A);
        const before = json(platform.saved);

        // Choosing a second plant mid-auction is illegal: the buffer must be rejected
        // even though its first move is legal.
        let error: Error | null = null;
        try {
            await platform.send([choose, choose], A);
        } catch (err) {
            error = err as Error;
        }
        expect(error, 'an illegal move mid-buffer must reject the whole buffer').to.not.be.null;

        // Nothing half-applied leaked into the platform's saved state...
        expect(json(platform.saved)).to.deep.equal(before);

        // ...and a valid buffer from that same state still works
        const ok = await platform.send([choose, openingBid(choose)], A);
        expect(ok.saved).to.be.true;
    });

    it('should reject a buffer that keeps playing past a turn boundary', async () => {
        // Degenerate case: the only other player is dropped, so the same player is up
        // again right after passing — [Pass, Pass] is a sequence of individually legal
        // moves that spans TWO turns (Resources, then Building). It must not commit
        // both for one time increment.
        const platform = new Platform(2, 'wrapper-test-boundary');
        const A = platform.saved.currentPlayers[0];
        const B = 1 - A;

        platform.saved = await wrapper.dropPlayer(platform.saved, B);

        // A buys the cheapest plant uncontested (B is dropped), ending the auction.
        await platform.send([cheapestChoosable(platform, A)], A);
        expect(platform.saved.phase).to.equal(Phase.Resources);
        expect(platform.saved.currentPlayers).to.deep.equal([A]);

        const before = json(platform.saved);

        let error: Error | null = null;
        try {
            await platform.send([pass, pass], A);
        } catch (err) {
            error = err as Error;
        }
        expect(error).to.not.be.null;
        expect(error!.message).to.match(/turn boundary/);
        expect(json(platform.saved)).to.deep.equal(before);

        // A buffer ending exactly on the turn boundary is still fine
        const ok = await platform.send([pass], A);
        expect(ok.saved).to.be.true;
        expect(platform.saved.phase).to.equal(Phase.Building);
        expect(platform.saved.currentPlayers).to.deep.equal([A]);
    });

    it('should play a full round-1 auction with the right commit points and a never-shrinking log', async () => {
        const platform = new Platform();
        const A = platform.saved.currentPlayers[0];
        const B = 1 - A;

        // A: choosing a plant is tentative (A must still open the bidding)...
        const chooseA = cheapestChoosable(platform, A);
        expect((await platform.send([chooseA], A)).saved).to.be.false;
        // ...and the opening bid hands control to B, committing A's turn.
        expect((await platform.send([chooseA, openingBid(chooseA)], A)).saved).to.be.true;
        expect(platform.saved.currentPlayers).to.deep.equal([B]);

        // B: passing the bidding is a single-move committed turn (A wins the auction,
        // the resolution events land in the log, and B is up to choose next).
        expect((await platform.send([pass], B)).saved).to.be.true;
        expect(platform.saved.players[A].powerPlants).to.have.length(1);
        expect(platform.saved.currentPlayers).to.deep.equal([B]);

        // B: the uncontested purchase commits immediately (the engine resolves the
        // auction at the minimum price and moves on to the Resources phase — under the
        // old rule the resolution events already made this un-undoable).
        expect((await platform.send([cheapestChoosable(platform, B)], B)).saved).to.be.true;
        expect(platform.saved.players[B].powerPlants).to.have.length(1);
        expect(platform.saved.phase).to.equal(Phase.Resources);

        // The saved log never shrank across committed states
        for (let i = 1; i < platform.logLengths.length; i++) {
            expect(platform.logLengths[i]).to.be.at.least(platform.logLengths[i - 1]);
        }
    });

    it('should commit each color pick as a single-move turn (chooseColors draft)', async () => {
        const platform = new Platform(2, 'wrapper-test-colors', { chooseColors: true });
        expect(platform.saved.phase).to.equal(Phase.ColorSelection);

        while (platform.saved.phase === Phase.ColorSelection) {
            const picker = platform.saved.currentPlayers[0];
            const color = platform.available(picker)[MoveName.ChooseColor]![0];
            const pick = await platform.send([{ name: MoveName.ChooseColor, data: color }], picker);
            expect(pick.saved, 'a color pick is never undoable').to.be.true;
        }

        expect(platform.saved.phase).to.equal(Phase.Auction);
        expect(platform.saved.players.every((pl) => !!pl.color)).to.be.true;
    });

    it('should keep fastBid bids as committed single-move turns and replay hidden-log states', async () => {
        const platform = new Platform(3, 'wrapper-test-fastbid', { fastBid: true });
        const A = platform.saved.currentPlayers[0];

        // Choosing the plant is tentative: with fastBid the chooser is one of the
        // simultaneous bidders and may still undo until their own (hidden) bid is in.
        const choose = cheapestChoosable(platform, A);
        expect((await platform.send([choose], A)).saved).to.be.false;

        // The chooser's own bid commits the turn: they leave currentPlayers, the other
        // bidders become current, and the bid sits in the hidden log.
        const openingBid: Move = { name: MoveName.Bid, data: choose.data as number };
        const opened = await platform.send([choose, openingBid], A);
        expect(opened.saved).to.be.true;
        expect(platform.saved.currentPlayers).to.have.length(2);
        expect(platform.saved.currentPlayers).to.not.include(A);
        expect(platform.saved.hiddenLog).to.have.length(1);

        // A second (hidden) bid: still mid-auction, still committed, two hidden moves.
        const B = platform.saved.currentPlayers[0];
        const bidB: Move = { name: MoveName.Bid, data: platform.available(B)[MoveName.Bid]![1] };
        expect((await platform.send([bidB], B)).saved).to.be.true;
        expect(platform.saved.hiddenLog).to.have.length(2);

        // An admin full-replay of the mid-auction save must reproduce it exactly,
        // hidden bids included.
        const replayed = wrapper.replay(cloneDeep(platform.saved));
        expect(json(replayed)).to.deep.equal(json(platform.saved));

        // The last bidder's pass resolves the auction and flushes the hidden log.
        const C = platform.saved.currentPlayers[0];
        expect((await platform.send([pass], C)).saved).to.be.true;
        expect(platform.saved.hiddenLog).to.have.length(0);
        expect(platform.saved.players[B].powerPlants, 'the higher bidder wins').to.have.length(1);
    });

    it('should tick the clocks deterministically across resends of the same buffer', async () => {
        const platform = new Platform(2, 'wrapper-test-clocks');
        const A = platform.saved.currentPlayers[0];
        const B = 1 - A;

        const t1 = 1_000_000;
        const t2 = 1_000_000 + 30_000;

        const choose: Move = { ...cheapestChoosable(platform, A), time: t1 };

        // The tentative call ticks the clocks of its (discarded) result the same way
        // the final replay will: the stamp travels with the move, not the wall clock.
        const mid = await platform.send([choose], A);
        expect(mid.result.players[A].clockStartedAt).to.equal(t1);

        const bid: Move = { ...openingBid(choose), time: t2 };
        const full = await platform.send([choose, bid], A);
        expect(full.saved).to.be.true;

        // A's turn banked exactly t2 - t1 (the clock started on their first stamped
        // move and stopped when the bid handed control to B).
        expect(platform.saved.players[A].totalTimeUsed).to.equal(t2 - t1);
        expect(platform.saved.players[A].clockStartedAt).to.be.undefined;
        expect(platform.saved.players[B].clockStartedAt).to.equal(t2);

        // Replaying the identical buffer from the same base reproduces identical clocks:
        // the tentative detour above changed nothing about the committed outcome.
        const again = await wrapper.move(setup(2, {}, 'wrapper-test-clocks'), [choose, bid], A);
        expect(json(again)).to.deep.equal(json(full.result));
        expect(again.players[A].totalTimeUsed).to.equal(t2 - t1);
    });

    it('should let two simultaneous Bureaucracy players commit independently (engine-level rebase)', async () => {
        const platform = new Platform(2, 'wrapper-test-bureaucracy');
        const { A, B } = await playToBureaucracy(platform);

        const moneyA = platform.saved.players[A].money;
        const moneyB = platform.saved.players[B].money;
        const basePayment = platform.saved.paymentTable[0];

        // A powers a plant: tentative (A can still undo their own powering even though
        // B is simultaneously current).
        const useA: Move = { name: MoveName.UsePowerPlant, data: platform.available(A)[MoveName.UsePowerPlant]![0] };
        const midA = await platform.send([useA], A);
        expect(midA.saved).to.be.false;
        expect(platform.saved.players[A].powerPlantsNotUsed, 'nothing persisted for A').to.have.length(1);

        // B commits their whole Bureaucracy turn on the committed base — which does
        // NOT contain A's tentative moves.
        const useB: Move = { name: MoveName.UsePowerPlant, data: platform.available(B)[MoveName.UsePowerPlant]![0] };
        const committedB = await platform.send([useB, pass], B);
        expect(committedB.saved).to.be.true;
        expect(platform.saved.players[B].money).to.equal(moneyB + basePayment);
        expect(platform.saved.currentPlayers).to.deep.equal([A]);

        // A's buffer REBASES onto the new committed state: the same moves are still
        // legal (each player's powering only touches their own resources), replay
        // cleanly, and A's Pass — the last one — commits and resolves the phase.
        expect(platform.available(A)[MoveName.UsePowerPlant], 'A can still power after B committed').to.not.be
            .undefined;
        const committedA = await platform.send([useA, pass], A);
        expect(committedA.saved).to.be.true;
        expect(platform.saved.players[A].money).to.be.greaterThanOrEqual(moneyA + basePayment);
        expect(platform.saved.round).to.equal(2);
        expect(platform.saved.phase).to.equal(Phase.Auction);
    });

    it('should always produce committed states from moveAI', async () => {
        let G = setup(3, {}, 'wrapper-test-ai');
        G.players.forEach((player, i) => {
            player.name = `AI ${i}`;
            player.isAI = true;
        });

        for (let turn = 0; turn < 60 && !wrapper.ended(G) && G.currentPlayers.length > 0; turn++) {
            const logLengthBefore = wrapper.logLength(G);
            G = wrapper.moveAI(G, G.currentPlayers[0]);

            expect(wrapper.toSave(G), `moveAI result of turn ${turn} must be saveable`).to.not.be.undefined;
            expect(wrapper.logLength(G)).to.be.at.least(logLengthBefore);
        }
    });

    it('should always produce committed states from dropPlayer', async () => {
        const G = setup(3, {}, 'wrapper-test-drop');
        const dropped = G.currentPlayers[0];

        // Dropping the current player auto-plays their whole pending turn (round 1
        // forces a purchase, so this exercises the moveAI loop, not the Pass shortcut).
        const result = await wrapper.dropPlayer(cloneDeep(G), dropped);

        expect(wrapper.toSave(result)).to.not.be.undefined;
        expect(result.players[dropped].isDropped).to.be.true;
        expect(result.currentPlayers).to.not.include(dropped);
        expect(result.players[result.currentPlayers[0]].availableMoves).to.not.be.null;
    });

    it('should not advance the turn when dropping a player who is not up', async () => {
        const G = setup(3, {}, 'wrapper-test-drop-idle');
        const current = [...G.currentPlayers];
        const idle = G.players.find((pl) => !current.includes(pl.id))!.id;

        const result = await wrapper.dropPlayer(cloneDeep(G), idle);

        expect(wrapper.toSave(result)).to.not.be.undefined;
        expect(result.players[idle].isDropped).to.be.true;
        expect(result.currentPlayers).to.deep.equal(current);
        expect(result.players[current[0]].availableMoves).to.not.be.null;
    });
});
