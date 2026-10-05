import { expect } from 'chai';
import { cloneDeep } from 'lodash';
import 'mocha';
import seedrandom from 'seedrandom';
import * as wrapper from '../wrapper';
import { bidRevision, canReopenPowering } from './choice-revisions';
import { setup } from './engine';
import { GameState, Phase, playerTimeUsed, PowerPlantType, ResourceType } from './gamestate';
import { Move, MoveName } from './move';

const pass: Move = { name: MoveName.Pass, data: true };

const json = (value: unknown) => JSON.parse(JSON.stringify(value));

describe('wrapper (tentative turns)', () => {
    // `wrapper.move` stamps each turn with the server clock (Date.now) so the per-player
    // clocks run off one clock instead of the acting client's skewed one. Pin it here so
    // a buffer replayed twice yields byte-identical states; a test that cares about elapsed
    // time advances the clock by mutating `now`. Restored after each test.
    const realNow = Date.now;
    const realRandom = Math.random;
    let now = 1_000_000;
    beforeEach(() => {
        now = 1_000_000;
        Date.now = () => now;
        Math.random = seedrandom('wrapper-test-choices');
    });
    afterEach(() => {
        Date.now = realNow;
        Math.random = realRandom;
    });

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

    it('replaces hidden fast bids without extra time, including changing a pass into a bid', async () => {
        const platform = new Platform(3, 'revisable-bid', { fastBid: true });
        const A = platform.saved.currentPlayers[0];
        const choose = cheapestChoosable(platform, A);
        await platform.send([choose, openingBid(choose)], A);
        const keyA = bidRevision(platform.saved, A)!;
        const increments = [...wrapper.timeIncrements(platform.saved)];
        const changed: Move = { name: MoveName.Bid, data: Number(choose.data) + 5, revision: keyA };
        expect(wrapper.canMoveOutOfTurn(platform.saved, changed, A)).to.equal(true);
        expect(wrapper.canMoveOutOfTurn(platform.saved, { ...pass, revision: keyA }, A)).to.equal(false);
        now += 10000;
        await platform.send(changed, A);
        expect(wrapper.isLiveUpdate(platform.saved)).to.equal(true);
        expect(wrapper.timeIncrements(platform.saved)).to.deep.equal(increments);
        expect(platform.saved.players[A].clockStartedAt).to.equal(undefined);
        expect(platform.saved.hiddenLog).to.have.length(1);
        const B = platform.saved.currentPlayers[0];
        await platform.send(pass, B);
        const keyB = bidRevision(platform.saved, B)!;
        await platform.send({ name: MoveName.Bid, data: Number(choose.data) + 6, revision: keyB }, B);
        expect(platform.saved.currentPlayers).to.have.length(1);
        expect(wrapper.replay(platform.saved).players[B].bid).to.equal(Number(choose.data) + 6);
        expect(wrapper.replay(platform.saved).players.map((p) => p.totalTimeUsed)).to.deep.equal(
            platform.saved.players.map((p) => p.totalTimeUsed)
        );
        const C = platform.saved.currentPlayers[0];
        await platform.send(pass, C);
        expect(platform.saved.players[B].powerPlants).to.have.length(1);
        expect(wrapper.canMoveOutOfTurn(platform.saved, changed, A)).to.equal(false);
    });

    it('reopens only the requester’s powering and never grants a second increment on confirmation', async () => {
        const platform = new Platform(2, 'revisable-power');
        const { A, B } = await playToBureaucracy(platform);
        const before = cloneDeep(platform.saved);
        const use: Move = { name: MoveName.UsePowerPlant, data: platform.available(A)[MoveName.UsePowerPlant]![0] };
        await platform.send([use, pass], A);
        const increments = [...wrapper.timeIncrements(platform.saved)];
        const reopen: Move = { name: MoveName.ReopenPowering, data: platform.saved.round };
        expect(canReopenPowering(platform.saved, A)).to.equal(true);
        expect(wrapper.canMoveOutOfTurn(platform.saved, reopen, B)).to.equal(false);
        now += 10000;
        await platform.send(reopen, A);
        expect(wrapper.isLiveUpdate(platform.saved)).to.equal(true);
        expect(wrapper.timeIncrements(platform.saved)).to.deep.equal(increments);
        expect(platform.saved.currentPlayers).to.have.members([A, B]);
        expect(platform.saved.players[A].money).to.equal(before.players[A].money);
        for (const field of ['coalLeft', 'oilLeft', 'garbageLeft', 'uraniumLeft', 'powerPlantsNotUsed'])
            expect(platform.saved.players[A][field]).to.deep.equal(before.players[A][field]);
        expect(platform.saved.players[B]).to.deep.equal(before.players[B]);
        expect(wrapper.stripSecret(platform.saved, B).poweringChoices?.[A]).to.equal(undefined);
        expect(wrapper.replay(platform.saved).players[A].money).to.equal(before.players[A].money);
        await platform.send(pass, A);
        expect(wrapper.timeIncrements(platform.saved)).to.deep.equal(increments);
        await platform.send(reopen, A);
        await platform.send([use, pass], A);
        expect(wrapper.timeIncrements(platform.saved)).to.deep.equal(increments);
        await platform.send(pass, B);
        expect(canReopenPowering(platform.saved, A)).to.equal(false);
        expect(wrapper.canMoveOutOfTurn(platform.saved, reopen, A)).to.equal(false);
        expect(wrapper.timeIncrements(platform.saved)[B]).to.equal(increments[B] + 1);
        expect(wrapper.replay(platform.saved).players[A].money).to.equal(platform.saved.players[A].money);
    });

    it('compacts repeated powering revisions and replays their fuel, income, and elapsed time exactly', async () => {
        const platform = new Platform(2, 'compact-power', { trackTotalSpent: true });
        const { A, B } = await playToBureaucracy(platform);
        const before = cloneDeep(platform.saved);
        const baseLength = before.log.length;
        const use: Move = {
            name: MoveName.UsePowerPlant,
            data: platform.available(A)[MoveName.UsePowerPlant]![0],
            time: 42,
        };
        now += 5_000;
        await platform.send([use, { ...pass, time: 43 }], A);
        const first = cloneDeep(platform.saved);
        const increments = [...wrapper.timeIncrements(first)];
        const firstStamps = first.log
            .slice(baseLength)
            .map((entry) => (entry.type === 'move' ? [entry.move.time, entry.move.serverTime] : []));
        const reopen: Move = { name: MoveName.ReopenPowering, data: before.round };
        for (let i = 0; i < 12; i++) {
            now += 10_000;
            await platform.send(reopen, A);
            expect(platform.saved.log).to.have.length(baseLength);
            expect(platform.saved.players[A].money).to.equal(before.players[A].money);
            expect(platform.saved.coalSupply).to.equal(before.coalSupply);
            expect(platform.saved.oilSupply).to.equal(before.oilSupply);
            expect(json(wrapper.replay(json(platform.saved)))).to.deep.equal(json(platform.saved));
            now += 2_000;
            await platform.send([use, pass], A);
            expect(platform.saved.log).to.have.length(baseLength + 2);
            expect(platform.saved.players[A].money).to.equal(first.players[A].money);
            expect(platform.saved.players[A].totalIncome).to.equal(first.players[A].totalIncome);
            expect(platform.saved.players[A].coalLeft).to.equal(first.players[A].coalLeft);
            expect(platform.saved.players[A].oilLeft).to.equal(first.players[A].oilLeft);
            expect(platform.saved.players[A].totalTimeUsed).to.equal(5_000 + (i + 1) * 2_000);
            expect(wrapper.timeIncrements(platform.saved)).to.deep.equal(increments);
            expect(
                platform.saved.log
                    .slice(baseLength)
                    .map((entry) => (entry.type === 'move' ? [entry.move.time, entry.move.serverTime] : []))
            ).to.deep.equal(firstStamps);
            expect(json(wrapper.replay(json(platform.saved)))).to.deep.equal(json(platform.saved));
        }
        now += 1_000;
        await platform.send(pass, B);
        expect(platform.saved.round).to.equal(before.round + 1);
        expect(json(wrapper.replay(json(platform.saved)))).to.deep.equal(json(platform.saved));
        expect(wrapper.canMoveOutOfTurn(platform.saved, reopen, A)).to.equal(false);
    });

    it('replays when the revised confirmation itself resolves Bureaucracy', async () => {
        const platform = new Platform(2, 'compact-last-reconfirmation');
        const { A, B } = await playToBureaucracy(platform);
        const round = platform.saved.round;
        now += 3_000;
        await platform.send(pass, A);
        now += 10_000;
        await platform.send({ name: MoveName.ReopenPowering, data: round }, A);
        now += 2_000;
        await platform.send(pass, B);
        expect(platform.saved.currentPlayers).to.deep.equal([A]);
        const increments = [...wrapper.timeIncrements(platform.saved)];
        now += 4_000;
        await platform.send(pass, A);
        expect(platform.saved.round).to.equal(round + 1);
        expect(wrapper.timeIncrements(platform.saved)).to.deep.equal(increments);
        expect(platform.saved.players[A].totalTimeUsed).to.equal(9_000);
        expect(json(wrapper.replay(json(platform.saved)))).to.deep.equal(json(platform.saved));
        for (let i = 0; platform.saved.round < round + 2 && i < 100; i++) {
            now += 1_000;
            platform.saved = wrapper.moveAI(platform.saved, platform.saved.currentPlayers[0]);
        }
        expect(platform.saved.round).to.equal(round + 2);
        expect(json(wrapper.replay(json(platform.saved)))).to.deep.equal(json(platform.saved));
    });

    for (const map of ['South Africa', 'Australia', 'India']) {
        it(`keeps ${map} fuel/income rules correct when a revised choice resolves upkeep`, async () => {
            const platform = new Platform(3, `compact-${map}`, { map, variant: 'recharged' });
            for (let i = 0; platform.saved.phase !== Phase.Bureaucracy && i < 200; i++)
                platform.saved = wrapper.moveAI(platform.saved, platform.saved.currentPlayers[0]);
            expect(platform.saved.phase).to.equal(Phase.Bureaucracy);
            const base = cloneDeep(platform.saved);
            const A = base.currentPlayers[0];
            now += 2_000;
            platform.saved = wrapper.moveAI(platform.saved, A);
            const choiceMoves = platform.saved.log
                .slice(base.log.length)
                .filter((entry) => entry.type === 'move')
                .map((entry) => (entry as import('./log').LogMove).move);
            const chosen = cloneDeep(platform.saved);
            now += 3_000;
            await platform.send({ name: MoveName.ReopenPowering, data: base.round }, A);
            for (const field of ['coalSupply', 'coalStorage', 'oilSupply', 'garbageSupply', 'uraniumSupply'])
                expect(platform.saved[field]).to.equal(base[field]);
            expect(platform.saved.players[A].money).to.equal(base.players[A].money);
            expect(platform.saved.players[A].targetCitiesPowered).to.equal(base.players[A].targetCitiesPowered);
            for (const B of base.currentPlayers.filter((seat) => seat !== A)) {
                now += 1_000;
                platform.saved = wrapper.moveAI(platform.saved, B);
            }
            now += 1_000;
            await platform.send(choiceMoves, A);
            expect(platform.saved.round).to.equal(base.round + 1);
            expect(wrapper.timeIncrements(platform.saved)[A]).to.equal(wrapper.timeIncrements(chosen)[A]);
            expect(json(wrapper.replay(json(platform.saved)))).to.deep.equal(json(platform.saved));
        });
    }

    it('keeps interleaved players’ powering choices, supports fewer plants, and migrates old snapshots', async () => {
        const platform = new Platform(3, 'compact-interleaved');
        for (let i = 0; platform.saved.phase !== Phase.Bureaucracy && i < 100; i++) {
            platform.saved = wrapper.moveAI(platform.saved, platform.saved.currentPlayers[0]);
        }
        expect(platform.saved.phase).to.equal(Phase.Bureaucracy);
        const [A, B, C] = platform.saved.currentPlayers;
        const before = cloneDeep(platform.saved);
        const baseLength = before.log.length;
        const use: Move = { name: MoveName.UsePowerPlant, data: platform.available(A)[MoveName.UsePowerPlant]![0] };
        expect(use.data).not.to.equal(undefined);
        now += 1_000;
        await platform.send([use, pass], A);
        now += 1_000;
        await platform.send(pass, B);
        const increments = [...wrapper.timeIncrements(platform.saved)];
        const savedB = cloneDeep(platform.saved.players[B]);
        const reopen: Move = { name: MoveName.ReopenPowering, data: before.round };
        // Simulate a save made by 2.0.12, before the first powering-log boundary existed.
        delete platform.saved.poweringChoices![A].logStart;
        delete platform.saved.poweringChoices![B].logStart;
        now += 1_000;
        await platform.send(reopen, A);
        expect(platform.saved.log).to.have.length(baseLength + 1);
        expect(json(platform.saved.players[B])).to.deep.equal(json(savedB));
        now += 1_000;
        await platform.send(reopen, B);
        expect(platform.saved.log).to.have.length(baseLength);
        expect(json(wrapper.replay(json(platform.saved)))).to.deep.equal(json(platform.saved));
        now += 1_000;
        await platform.send(pass, A);
        now += 1_000;
        await platform.send(pass, B);
        expect(platform.saved.log).to.have.length(baseLength + 2);
        expect(wrapper.timeIncrements(platform.saved)).to.deep.equal(increments);
        expect(platform.saved.players[A].powerPlantsNotUsed).to.deep.equal(before.players[A].powerPlantsNotUsed);
        expect(platform.saved.coalSupply).to.equal(before.coalSupply);
        expect(platform.saved.oilSupply).to.equal(before.oilSupply);
        expect(json(wrapper.replay(json(platform.saved)))).to.deep.equal(json(platform.saved));
        now += 1_000;
        await platform.send({ ...pass, poweringClock: { at: 0, totalTimeUsed: 0 } }, C);
        expect(playerTimeUsed(platform.saved.players[C], now)).to.be.at.least(7_000);
        expect(platform.saved.round).to.equal(before.round + 1);
        expect(json(wrapper.replay(json(platform.saved)))).to.deep.equal(json(platform.saved));
    });

    it('should drive the per-player clocks from the server clock, immune to client skew', async () => {
        // The absurd client `time`s below stand in for skewed browser clocks — banking a
        // stretch subtracts one player's stamp from another's, so before turns were
        // server-stamped a fast client charged its skew to itself every turn, creeping
        // toward the whole game's elapsed time. None of these client stamps may reach a
        // timer (the shared `now`, pinned at 1_000_000, is the only clock that counts).
        const platform = new Platform(2, 'wrapper-test-clocks');
        const A = platform.saved.currentPlayers[0];
        const B = 1 - A;

        const skew = (m: Move, t: number): Move => ({ ...m, time: t });

        // A opens the auction and commits at server time 1_000_000. Whatever nonsense
        // client stamps the moves carry, control passing to B starts B's clock on the
        // SERVER clock, and A's (single-buffer) stretch is banked and cleared.
        const choose = cheapestChoosable(platform, A);
        await platform.send([skew(choose, 9_000_000_000), skew(openingBid(choose), 3)], A);
        expect(platform.saved.players[B].clockStartedAt).to.equal(1_000_000);
        expect(platform.saved.players[A].clockStartedAt).to.be.undefined;

        // Finish the auction (still at 1_000_000, so these stretches are ~0) to reach
        // the sequential Resources phase.
        await platform.send([skew(pass, 1)], B);
        await platform.send([skew(cheapestChoosable(platform, B), 2)], B);
        expect(platform.saved.phase).to.equal(Phase.Resources);

        // The first Resources player is on the clock from the phase start (1_000_000).
        const R = platform.saved.currentPlayers[0];
        expect(platform.saved.players[R].clockStartedAt).to.equal(1_000_000);

        // 25 minutes of SERVER time pass; the client stamp is nonsense. The stretch
        // banked is the server span, not anything derived from the client stamp.
        now = 1_000_000 + 25 * 60_000;
        await platform.send([skew(pass, 42)], R);
        expect(platform.saved.players[R].totalTimeUsed).to.equal(25 * 60_000);
        expect(platform.saved.players[R].clockStartedAt).to.be.undefined;

        // Replay reads the server stamps stored in the log, never the wall clock, so
        // it reproduces the identical clocks even though Date.now has moved on.
        now = 987_654_321;
        const replayed = wrapper.replay(cloneDeep(platform.saved));
        expect(replayed.players.map((p) => p.totalTimeUsed)).to.deep.equal(
            platform.saved.players.map((p) => p.totalTimeUsed)
        );
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

    it('should only hand back a state from logSlice when it knows whose it is', async () => {
        // `GET /gameplay/:id/log` is not logged-in: it resolves the player with
        // `findIndex`, which is -1 when there is no user. `stripSecret` then blanks
        // EVERY player's availableMoves, so adopting that state left the acting
        // player looking at a live board with nothing clickable until they re-entered
        // the game. Without `state` the viewer falls back to `fetchState`.
        const G = setup(3, {}, 'wrapper-test-log-slice');
        const current = G.currentPlayers[0];

        const known = wrapper.logSlice(G, { player: current });
        expect(known.state, 'a known player still gets the state').to.not.be.undefined;
        expect(Object.keys(known.state!.players[current].availableMoves!), 'and it keeps their own available moves').to
            .not.be.empty;

        expect(wrapper.logSlice(G, { player: -1 }).state, 'unresolved user (-1): no state').to.be.undefined;
        expect(wrapper.logSlice(G, {}).state, 'no player given: no state').to.be.undefined;
        expect(wrapper.logSlice(G).state, 'no options at all: no state').to.be.undefined;

        // The log itself is public and must keep flowing either way.
        expect(wrapper.logSlice(G, { player: -1 }).log, 'the log is still served').to.deep.equal(G.log);
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

describe('analysis adapter', () => {
    it('clears automation, preserves tentative turns and keeps every seat manual', async () => {
        const source = setup(3, {}, 'analysis');
        source.players[1].isDropped = true;
        const original = json(source);
        let copy = wrapper.createAnalysis(source, { to: source.log.length, sourceEnded: true });
        expect(copy.players.every((p) => !p.isDropped)).to.equal(true);
        expect(copy.automation).to.equal(undefined);
        const actor = copy.currentPlayers[0];
        const available = copy.players[actor].availableMoves!;
        const name = Object.keys(available)[0] as MoveName;
        const data = (available[name] as any[])[0];
        copy = await wrapper.analysisMove(copy, { name, data } as Move, actor);
        expect(copy.automation).to.equal(undefined);
        expect(copy.log.length).to.be.greaterThan(original.log.length);
        expect(json(source)).to.deep.equal(original);
    });
});
