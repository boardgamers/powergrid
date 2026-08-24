import { resourceBlocks } from '@/util/resource-rows';
import { expect } from 'chai';
import type { GameState } from 'powergrid-engine';
import { availableMoves, move as engineMove, moveAI, MoveName, Phase, setup } from 'powergrid-engine';

/**
 * The portrait market shows a price on every box. The only way that number can be
 * trusted is to spend it: buy one cube from each row and check the engine took
 * exactly what the box said it would.
 *
 * This is the check that would have caught Central Europe, where the engine sells
 * garbage a dollar cheaper to whoever holds Wien — the price on the board and the
 * price a given player pays are not the same number.
 */
describe('resource-rows', () => {
    const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value));

    // moveAI draws from raw Math.random, not the game seed, so an unpinned walk to a
    // mid-game position lands somewhere different every run — and on India it can walk
    // into the known Bureaucracy dead-end and never arrive at all. Pin the dice for the
    // walk so the positions these tests describe are the same ones every time.
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

    /** Play until `seat` is buying resources in at least `minRound`. */
    function resourcesSeat(map: string, players: number, seed: string, minRound: number, seat: number, dice = 1) {
        pinDice(dice);
        let G: GameState = setup(players, { map, variant: 'recharged' } as never, seed);
        for (let i = 0; i < 40000; i++) {
            const moves = G.players[seat].availableMoves;
            if (G.round >= minRound && G.phase === Phase.Resources && moves && moves[MoveName.BuyResource]) return G;
            const idx = G.players.findIndex((p) => p.availableMoves);
            if (idx < 0) return null;
            try {
                G = moveAI(G, idx);
            } catch {
                return null;
            }
        }
        return null;
    }

    // map, players, seed, min round, pinned dice
    const boards: [string, number, string, number, number][] = [
        ['Germany', 4, '5', 4, 1],
        ['Korea', 4, '2', 5, 1],
        ['India', 4, '7', 6, 7],
        ['South Africa', 4, '3', 5, 1],
        ['Australia', 4, '7', 8, 1],
        ['Europe', 4, '1', 5, 1],
        ['Middle East', 4, '3', 4, 1],
        ['Bremen', 4, '0', 5, 1],
        ['USA', 4, '3', 8, 1],
        ['Central Europe', 4, '4', 5, 1],
    ];

    it('every price a box shows is the money the engine actually takes', () => {
        const seat = 1;
        let rowsChecked = 0;

        for (const [map, players, seed, minRound, dice] of boards) {
            const G = resourcesSeat(map, players, seed, minRound, seat, dice);
            expect(G, `${map} never reached a resource-buying seat`).to.not.be.null;

            const buyable = G!.players[seat].availableMoves![MoveName.BuyResource]!;
            const blocks = resourceBlocks(G!, {
                player: seat,
                buyable,
                isUsaRecharged: G!.options.variant === 'recharged' && G!.map.name === 'USA',
            });

            for (const block of blocks) {
                for (const row of block.rows) {
                    if (!row.buyable) continue;
                    const before = G!.players[seat].money;
                    const after = engineMove(
                        clone(G!),
                        { name: MoveName.BuyResource, data: row.move, time: 1 } as never,
                        seat
                    );
                    expect(before - after.players[seat].money, `${map}: ${row.label} box says $${row.price}`).to.equal(
                        row.price
                    );
                    rowsChecked++;
                }
            }
        }

        expect(rowsChecked, 'no buyable rows were exercised at all').to.be.greaterThan(15);
    });

    it('the Wien garbage discount reaches the box, not just the engine', () => {
        const seat = 1;
        const G = resourcesSeat('Central Europe', 4, '4', 5, seat);
        expect(G, 'no Central Europe seat').to.not.be.null;

        const priceOf = (state: GameState) => {
            const rows = resourceBlocks(state, { player: seat }).flatMap((b) => b.rows);
            return rows.find((r) => r.label === 'Garbage')!.price;
        };

        const withoutWien = clone(G!);
        withoutWien.players[seat].cities = withoutWien.players[seat].cities.filter((c) => c.name !== 'Wien');
        const printed = priceOf(withoutWien);

        // Give the seat Wien and nothing else changes.
        const withWien = clone(withoutWien);
        withWien.players[seat].cities.push({ name: 'Wien', region: 'red' } as never);

        expect(priceOf(withWien), 'a Wien holder pays a dollar less').to.equal(printed! - 1);

        // And the engine agrees, which is the whole reason the box may show it. The
        // two states were edited by hand, so re-derive what each seat may do before
        // asking the engine to act — `move` checks the payload against that list.
        const buy = { name: MoveName.BuyResource, data: { resource: 'garbage' }, time: 1 };
        const paidFrom = (state: GameState) => {
            state.players[seat].availableMoves = availableMoves(state, state.players[seat]);
            state.currentPlayers = [seat];
            return state.players[seat].money - engineMove(clone(state), buy as never, seat).players[seat].money;
        };
        expect(paidFrom(withoutWien), 'the engine charges the printed price without Wien').to.equal(printed);
        expect(paidFrom(withWien), 'and a dollar less with it').to.equal(printed! - 1);
    });

    it('a map with no uranium on the track gets no uranium box', () => {
        for (const [map, expected] of [
            ['Australia', false],
            ['Bremen', false],
            ['Germany', true],
        ] as [string, boolean][]) {
            const G = setup(4, { map, variant: 'recharged' } as never, '7');
            const labels = resourceBlocks(G).flatMap((b) => b.rows.map((r) => r.label));
            expect(labels.includes('Uranium'), `${map} uranium row`).to.equal(expected);
        }
    });

    it('Korea gets one block per side, and only the south side sells uranium', () => {
        const G = setup(4, { map: 'Korea', variant: 'recharged' } as never, '2');
        const blocks = resourceBlocks(G, { resupply: ['3', '2', '1', '1'], resupplyNorth: ['2', '1', '1'] });

        expect(blocks.map((b) => b.title)).to.deep.equal(['North Market', 'South Market']);
        expect(blocks[0].rows.map((r) => r.label)).to.deep.equal(['Coal', 'Oil', 'Garbage']);
        expect(blocks[1].rows.map((r) => r.label)).to.deep.equal(['Coal', 'Oil', 'Garbage', 'Uranium']);
        expect(blocks[0].rows.every((r) => r.move.side === 'north')).to.be.true;
        expect(blocks[1].rows.every((r) => r.move.side === 'south')).to.be.true;

        // The restock numbers line up with the boxes drawn under them.
        expect(blocks[0].restock).to.equal('2 / 1 / 1');
        expect(blocks[1].restock).to.equal('3 / 2 / 1 / 1');
    });

    it("South Africa's storage pool is its own row at a flat price", () => {
        const G = setup(4, { map: 'South Africa', variant: 'recharged' } as never, '3');
        G.coalStorage = 6;
        const rows = resourceBlocks(G).flatMap((b) => b.rows);
        const storage = rows.find((r) => r.move.fromStorage)!;

        expect(storage, 'a storage row exists').to.not.be.undefined;
        expect(storage.price).to.equal(8);
        expect(storage.flat, 'no price track behind it').to.be.true;
        // Dots would claim only some cubes are at this price. They all are.
        expect(storage.atPrice).to.equal(0);
        expect(storage.cubes).to.equal(6);
        // It does not steal a restock number from the printed rows.
        const block = resourceBlocks(G, { resupply: ['5', '2', '2', '2'] })[0];
        expect(block.restock).to.equal('5 / 2 / 2 / 2');
    });

    it('a row above the per-step price cap is shown, and flagged as unbuyable', () => {
        const G = setup(4, { map: 'India', variant: 'recharged' } as never, '7');
        expect(G.step, 'India starts in step 1').to.equal(1);
        expect((G.map as { maxPriceAvailable?: number[] }).maxPriceAvailable![0], 'step 1 cap').to.equal(3);

        G.uraniumMarket = 1; // drives the next uranium cube to the dear end of the track
        const uranium = resourceBlocks(G)
            .flatMap((b) => b.rows)
            .find((r) => r.label === 'Uranium')!;

        expect(uranium.price! > 3, 'the next cube is above the cap').to.be.true;
        expect(uranium.capped).to.be.true;
        expect(uranium.buyable, 'nobody may buy it yet').to.be.false;
    });

    it('an empty market reads as out rather than as free', () => {
        const G = setup(4, { map: 'Germany', variant: 'recharged' } as never, '5');
        G.coalMarket = 0;
        const coal = resourceBlocks(G)
            .flatMap((b) => b.rows)
            .find((r) => r.label === 'Coal')!;

        expect(coal.price).to.be.null;
        expect(coal.next).to.be.null;
        expect(coal.atPrice).to.equal(0);
        expect(coal.cubes).to.equal(0);
    });
});
