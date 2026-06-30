import { expect } from 'chai';
import 'mocha';
import { availableMoves, computeRegionGraph, regionPickable } from './available-moves';
import {
    applyAustraliaStep3Shift,
    applyManhattanMarketLifecycle,
    ended,
    getPowerPlant,
    move,
    reconstructState,
    setup,
} from './engine';
import GermanyRecharged from './fixtures/GermanyRecharged.json';
import supply from './fixtures/supply.json';
import undo from './fixtures/undo.json';
import USAOriginal from './fixtures/USAOriginal.json';
import {
    GameOptions,
    MapName,
    Phase,
    PowerPlant,
    PowerPlantType,
    resupplyUraniumMine,
    sellUraniumMine,
    Variant,
} from './gamestate';
import { Move, MoveName } from './move';
import { powerPlants } from './powerPlants';

describe('Engine', () => {
    it('should setup a game correctly', () => {
        const G = setup(5, { fastBid: false }, 'test');

        expect(ended(G)).to.false;
    });

    it('should play full game Germany recharged', () => {
        const game = GermanyRecharged;
        const options: GameOptions = {
            fastBid: game.options.fastBid,
            map: game.options.map as MapName,
            showMoney: game.options.showMoney,
            variant: game.options.variant as Variant,
            useNewRechargedSetup: game.options.useNewRechargedSetup,
        };

        expect(options.useNewRechargedSetup).to.be.false;

        let G = setup(game.players.length, options, game.seed);

        for (const item of game.log) {
            if (item.type === 'move') {
                G = move(G, item.move! as Move, item.player!);
            }
        }

        expect(G.currentPlayers).to.deep.equal([]);
        expect(ended(G)).to.be.true;
    });

    it('should replay game Germany recharged', () => {
        const game = GermanyRecharged;

        expect(game.options.useNewRechargedSetup).to.be.false;

        const G = reconstructState(game as any, game.log.length - 1);

        expect(ended(G)).to.be.true;
    });

    it('should replay game without seed Germany recharged', () => {
        const game = GermanyRecharged;
        const options: GameOptions = {
            fastBid: game.options.fastBid,
            map: game.options.map as MapName,
            showMoney: game.options.showMoney,
            variant: game.options.variant as Variant,
            useNewRechargedSetup: game.options.useNewRechargedSetup,
        };

        expect(options.useNewRechargedSetup).to.be.false;

        let G = setup(game.players.length, options, game.seed);

        for (const item of game.log) {
            if (item.type === 'move') {
                G = move(G, item.move! as Move, item.player!);
            }
        }

        expect(G.currentPlayers).to.deep.equal([]);
        expect(ended(G)).to.be.true;

        G.seed = 'secret';
        G = reconstructState(G, G.log.length - 2);

        expect(ended(G)).to.be.false;
    });

    it('should play full game USA original', () => {
        const game = USAOriginal;
        const options: GameOptions = {
            fastBid: game.options.fastBid,
            map: game.options.map as MapName,
            showMoney: game.options.showMoney,
            variant: game.options.variant as Variant,
        };

        let G = setup(game.players.length, options, game.seed);

        for (const item of game.log) {
            if (item.type === 'move') {
                G = move(G, item.move! as Move, item.player!);
            }
        }

        expect(G.currentPlayers).to.deep.equal([]);
        expect(ended(G)).to.be.true;
    });

    it('should replay game USA original', () => {
        const game = USAOriginal;

        const G = reconstructState(game as any, game.log.length - 1);

        expect(ended(G)).to.be.true;
    });

    it('should replay game without seed USA original', () => {
        const game = USAOriginal;
        const options: GameOptions = {
            fastBid: game.options.fastBid,
            map: game.options.map as MapName,
            showMoney: game.options.showMoney,
            variant: game.options.variant as Variant,
        };

        let G = setup(game.players.length, options, game.seed);

        for (const item of game.log) {
            if (item.type === 'move') {
                G = move(G, item.move! as Move, item.player!);
            }
        }

        expect(G.currentPlayers).to.deep.equal([]);
        expect(ended(G)).to.be.true;

        G.seed = 'secret';
        G = reconstructState(G, G.log.length - 2);

        expect(ended(G)).to.be.false;
    });

    it('should replay game supply', () => {
        const game = supply;

        const G = reconstructState(game as any, game.log.length - 1);

        expect(ended(G)).to.be.false;
    });

    it('should setup Korea with dual-market populated and players ready to move', () => {
        // Smoke test for the Korea map (PR #74). If a deployed lobby fails to
        // auto-start, setup() is the most likely culprit — this catches that
        // class of bug without needing a recorded game fixture.
        const G = setup(
            2,
            { map: 'Korea', variant: 'recharged', randomizeMap: false, fastBid: false },
            'korea-test-seed'
        );

        expect(ended(G)).to.be.false;
        expect(G.map.name).to.equal('Korea');

        // South-side markets (standard fields, uranium only here)
        expect(G.coalMarket).to.be.greaterThan(0);
        expect(G.oilMarket).to.be.greaterThan(0);
        expect(G.uraniumMarket).to.be.greaterThan(0);

        // North-side markets (Korea-specific, no uranium row)
        expect(G.coalMarketNorth).to.be.greaterThan(0);
        expect(G.oilMarketNorth).to.be.greaterThan(0);
        expect(G.garbageMarketNorth).to.exist;

        // Korea uses parallel per-side price tables
        expect(G.coalPricesNorth).to.be.an('array').that.is.not.empty;
        expect(G.oilPricesNorth).to.be.an('array').that.is.not.empty;

        // At least one player should have available moves (auction phase is live)
        expect(G.players.some((p) => p.availableMoves && Object.keys(p.availableMoves).length > 0)).to.be.true;
    });

    it('should setup Northern Europe and have players ready to move', () => {
        // Smoke test for Northern Europe (PR #74) — parity with Korea test.
        const G = setup(
            2,
            { map: 'Northern Europe', variant: 'recharged', randomizeMap: false, fastBid: false },
            'ne-test-seed'
        );

        expect(ended(G)).to.be.false;
        expect(G.map.name).to.equal('Northern Europe');
        expect(G.players.some((p) => p.availableMoves && Object.keys(p.availableMoves).length > 0)).to.be.true;
    });

    it('should preserve regionalPowerPlants override when chosen for auction', () => {
        // Regression: ChoosePowerPlant previously used getPowerPlant() canonical
        // lookup, losing regionalPowerPlants overrides — Mike reported plants in
        // Northern Europe reverting from regional (e.g. coal/3-cities) to canonical
        // (wind/2-cities) on bid selection.
        const G = setup(
            5,
            { map: 'Northern Europe', variant: 'recharged', randomizeMap: false, fastBid: false },
            'ne-test-seed'
        );

        // Find a regional plant whose values differ from canonical and is currently
        // in the market or deck, then place it into actualMarket[0] so it's choosable.
        const overrides = (G.map as any).regionalPowerPlants as Record<string, PowerPlant[]>;
        const regionsInPlay = new Set(G.map.cities.map((c) => c.region));

        let regional: PowerPlant | undefined;
        for (const region of regionsInPlay) {
            for (const override of overrides[region] ?? []) {
                const canonical = getPowerPlant(override.number);
                if (
                    canonical.type !== override.type ||
                    canonical.citiesPowered !== override.citiesPowered ||
                    canonical.cost !== override.cost
                ) {
                    const found = [...G.actualMarket, ...G.futureMarket, ...G.powerPlantsDeck].find(
                        (p) => p.number === override.number
                    );
                    if (found) {
                        regional = found;
                        break;
                    }
                }
            }
            if (regional) break;
        }

        expect(regional, 'expected at least one regional plant in play with this seed').to.exist;

        // Swap the regional plant into actualMarket[0] and recompute the starting
        // player's available moves so they can choose it.
        G.actualMarket[0] = regional!;
        const startingPlayer = G.currentPlayers[0];
        G.players[startingPlayer].money = 100; // ensure they can afford the plant
        G.players[startingPlayer].availableMoves = availableMoves(G, G.players[startingPlayer]);

        const G2 = move(G, { name: MoveName.ChoosePowerPlant, data: regional!.number } as Move, startingPlayer);

        // Chosen plant must be the regional version, not canonical.
        const canonical = getPowerPlant(regional!.number);
        expect(G2.chosenPowerPlant).to.exist;
        expect(G2.chosenPowerPlant!.number).to.equal(regional!.number);
        expect(G2.chosenPowerPlant!.type).to.equal(regional!.type);
        expect(G2.chosenPowerPlant!.citiesPowered).to.equal(regional!.citiesPowered);
        expect(G2.chosenPowerPlant!.cost).to.equal(regional!.cost);
        // Sanity: the override must actually differ from canonical, otherwise the
        // test wouldn't catch the bug.
        expect(
            G2.chosenPowerPlant!.type !== canonical.type ||
                G2.chosenPowerPlant!.citiesPowered !== canonical.citiesPowered ||
                G2.chosenPowerPlant!.cost !== canonical.cost
        ).to.be.true;
    });

    it('should forbid uranium plants for Northern Europe players with no valid-region cities', () => {
        // Mike's feedback: round 1 has no cities yet, so no player should be able to
        // bid on uranium. More generally, players need at least one city in Sweden
        // (purple/yellow), Finland (brown), or the Baltic States (pink). Norway (red)
        // and Denmark (orange) alone do not qualify.
        const G = setup(
            5,
            { map: 'Northern Europe', variant: 'recharged', randomizeMap: false, fastBid: false },
            'ne-uranium-seed'
        );

        // Inject a uranium plant into the visible market so the test is meaningful
        // regardless of seed (canonical plant 17 is a uranium plant priced 17).
        const uraniumPlant = getPowerPlant(17);
        expect(uraniumPlant.type).to.equal(PowerPlantType.Uranium);
        G.actualMarket[0] = uraniumPlant;

        for (const player of G.players) {
            player.money = 100; // afford filter must not be what hides it
            player.availableMoves = availableMoves(G, player);
            const choosable = (player.availableMoves?.[MoveName.ChoosePowerPlant] ?? []) as number[];
            expect(
                choosable.includes(uraniumPlant.number),
                `player ${player.id} (no cities yet) must not be able to choose a uranium plant`
            ).to.be.false;
        }
    });

    it('should reduce Europe deck with weak/main split for low player counts', () => {
        // Europe (recharged) deck reduction, split plug (<=15) vs socket (>15), per the
        // USA Recharged rulebook and confirmed with Mike: 2P removes 1 plug + 5 socket,
        // 3P removes 2 plug + 6 socket, 4P removes 1 plug + 3 socket, 5+P removes nothing.
        // (The original edition removes 8 at 2P — that's the separate variant == 'original' path.)
        // The engine ships one combined plant set, so "plug" = the low (<=15) band, the
        // same convention the Recharged default setup uses for its initial-market reserve.
        // Total plants = 42 + step3. Opening market draw is 9 (4 actual + 5 future), all
        // from the plug pool; Step 3 is buried at the bottom. Deck length after setup:
        //   2P:   42 - 9 - 6 = 27, plus step3 = 28
        //   3P:   42 - 9 - 8 = 25, plus step3 = 26
        //   4P:   42 - 9 - 4 = 29, plus step3 = 30
        //   5+P:  42 - 9     = 33, plus step3 = 34
        const expectedSize: Record<number, number> = { 2: 28, 3: 26, 4: 30, 5: 34, 6: 34 };
        const expectedWeakRemoved: Record<number, number> = { 2: 1, 3: 2, 4: 1, 5: 0, 6: 0 };
        const expectedMainRemoved: Record<number, number> = { 2: 5, 3: 6, 4: 3, 5: 0, 6: 0 };

        for (const numPlayers of [2, 3, 4, 5, 6]) {
            const G = setup(
                numPlayers,
                { map: 'Europe', variant: 'recharged', randomizeMap: false },
                `eu-trim-${numPlayers}p`
            );

            expect(G.powerPlantsDeck.length, `Europe ${numPlayers}P deck size`).to.equal(expectedSize[numPlayers]);
            expect(G.actualMarket.length).to.equal(4);
            expect(G.futureMarket.length).to.equal(5);
            // Step 3 is the last card in the deck.
            expect(G.powerPlantsDeck[G.powerPlantsDeck.length - 1].type).to.equal(PowerPlantType.Step3);

            // Verify the weak/main split: compare the numbers still visible (market
            // + future + deck) against the canonical set of plant numbers to see
            // which were removed.
            const visibleNumbers = new Set<number>([
                ...G.actualMarket.map((p) => p.number),
                ...G.futureMarket.map((p) => p.number),
                ...G.powerPlantsDeck.map((p) => p.number),
            ]);
            const removed: number[] = [];
            for (const p of powerPlants) {
                if (p.type !== PowerPlantType.Step3 && !visibleNumbers.has(p.number)) {
                    removed.push(p.number);
                }
            }
            const weakRemoved = removed.filter((n) => n <= 15).length;
            const mainRemoved = removed.filter((n) => n > 15).length;
            expect(weakRemoved, `Europe ${numPlayers}P weak cards removed`).to.equal(expectedWeakRemoved[numPlayers]);
            expect(mainRemoved, `Europe ${numPlayers}P main cards removed`).to.equal(expectedMainRemoved[numPlayers]);
        }
    });

    it('should place UK & Ireland Step 3 card third from last with two plants below it', () => {
        // UK & Ireland rules: the Step 3 card (plant 99) goes at deck.length - 3
        // so two plants sit below it, and Step 3 fires two auctions earlier than
        // a standard "Step 3 at the bottom" deck.
        const G = setup(5, { map: 'UK & Ireland', variant: 'recharged', randomizeMap: false }, 'ukireland-test-seed');

        const step3Idx = G.powerPlantsDeck.findIndex((p) => p.number === 99);
        expect(step3Idx).to.equal(G.powerPlantsDeck.length - 3);

        // The two plants below Step 3 are real plants (not another Step 3 card or
        // undefined slots).
        expect(G.powerPlantsDeck[step3Idx + 1]).to.exist;
        expect(G.powerPlantsDeck[step3Idx + 2]).to.exist;
        expect(G.powerPlantsDeck[step3Idx + 1].number).to.not.equal(99);
        expect(G.powerPlantsDeck[step3Idx + 2].number).to.not.equal(99);
    });

    it('should never strand a UK & Ireland region from the rest of its landmass', () => {
        // The region picker may split Great Britain from Ireland (no sea edge —
        // the cross-island surcharge bridges them), but the regions chosen WITHIN
        // a landmass must stay mutually connected. A region stranded on its own
        // island (e.g. Scotland without N. England) is unreachable for anyone who
        // didn't start there, which soft-locks Step 2 / the end game. Sweep many
        // seeds across player counts and assert each landmass's chosen regions
        // form a single connected component.
        for (let pc = 2; pc <= 6; pc++) {
            for (let s = 0; s < 30; s++) {
                const G = setup(
                    pc,
                    { map: 'UK & Ireland', variant: 'recharged', randomizeMap: false },
                    `uki-conn-${pc}-${s}`
                );
                const cities = G.map.cities;

                const regionIsland: Record<string, string> = {};
                cities.forEach((c) => {
                    if (c.island) regionIsland[c.region] = c.island;
                });

                const regionsInPlay = [...new Set(cities.map((c) => c.region))];
                const adj: Record<string, Set<string>> = {};
                regionsInPlay.forEach((r) => (adj[r] = new Set<string>()));
                G.map.connections.forEach((con) => {
                    const a = cities.find((c) => c.name === con.nodes[0])!.region;
                    const b = cities.find((c) => c.name === con.nodes[1])!.region;
                    if (a !== b) {
                        adj[a].add(b);
                        adj[b].add(a);
                    }
                });

                const byIsland: Record<string, string[]> = {};
                regionsInPlay.forEach((r) => {
                    const isl = regionIsland[r];
                    if (!byIsland[isl]) byIsland[isl] = [];
                    byIsland[isl].push(r);
                });

                for (const isl of Object.keys(byIsland)) {
                    const group = byIsland[isl];
                    const seen = new Set<string>([group[0]]);
                    const queue = [group[0]];
                    while (queue.length) {
                        const cur = queue.shift()!;
                        adj[cur].forEach((nb) => {
                            if (regionIsland[nb] === isl && !seen.has(nb)) {
                                seen.add(nb);
                                queue.push(nb);
                            }
                        });
                    }
                    expect(
                        seen.size,
                        `players=${pc} seed=uki-conn-${pc}-${s} island=${isl} regions=[${group}] not internally connected`
                    ).to.equal(group.length);
                }
            }
        }
    });

    it('should only offer the UK & Ireland cross-island jump into empty cities', () => {
        const G = setup(5, { map: 'UK & Ireland', variant: 'recharged', randomizeMap: false }, 'uki-jump');
        G.phase = Phase.Building;
        G.step = 2; // second houses are open to same-island networks, but NOT to the jump
        const player = G.players[0];
        player.money = 200;

        const gbCity = G.map.cities.find((c) => c.island === 'gb')!;
        const ieCities = G.map.cities.filter((c) => c.island === 'ie');
        player.cities = [{ name: gbCity.name, position: 0 }];
        // Another player already holds a house in one Irish city.
        G.players[1].cities = [{ name: ieCities[0].name, position: 0 }];

        const builds = availableMoves(G, player)[MoveName.Build] as { name: string; price: number }[];
        const priceOf = (name: string) => builds.find((b) => b.name === name)?.price;

        const occupied = priceOf(ieCities[0].name);
        expect(occupied === undefined || occupied === 9999, 'occupied Irish city not jumpable in Step 2').to.be.true;
        // An empty Irish city is jumpable as a first house: 10 + 20 surcharge.
        expect(priceOf(ieCities[1].name), 'empty Irish city jumpable at 30').to.equal(30);
    });

    it('should remove uranium plant 17 from the Australia deck and keep the five mines', () => {
        // Australia replaces the six uranium plants with mines: plant 17 is removed
        // from the deck entirely, while 11/23/28/34/39 stay in (and behave as
        // uranium mines). Use 5P so no low-player-count deck reduction can randomly
        // drop a mine.
        for (const variant of ['recharged', 'original'] as const) {
            const G = setup(5, { map: 'Australia', variant, randomizeMap: false }, `australia-deck-${variant}`);

            const allNumbers = new Set<number>([
                ...G.actualMarket.map((p) => p.number),
                ...G.futureMarket.map((p) => p.number),
                ...G.powerPlantsDeck.map((p) => p.number),
            ]);

            expect(allNumbers.has(17), `Australia ${variant}: plant 17 removed`).to.be.false;
            for (const mine of [11, 23, 28, 34, 39]) {
                expect(allNumbers.has(mine), `Australia ${variant}: mine ${mine} present`).to.be.true;
            }
        }
    });

    it('should cap Australia connection costs at 20 (general connection), incl. jumps to disconnected regions', () => {
        // Use 5P so all five regions are in play (Red/WA is otherwise droppable).
        const G = setup(5, { map: 'Australia', variant: 'recharged', randomizeMap: false }, 'australia-build-cap');
        G.phase = Phase.Building;
        G.step = 1;

        const player = G.players[0];
        player.money = 100;
        player.cities = [{ name: 'Perth', position: 0 }];

        const builds = availableMoves(G, player)[MoveName.Build] as { name: string; price: number }[];
        const priceOf = (name: string) => builds.find((b) => b.name === name)?.price;

        // Reachable within WA: the Perth–Bunbury edge is 4, below the 20 cap, so the
        // real path is paid — 4 connection + 10 first-slot = 14.
        expect(priceOf('Bunbury'), 'Bunbury (cheap, reachable)').to.equal(14);

        // Sydney is in a different region with no inter-region edge to WA, so dijkstra
        // reports it unreachable; the general connection caps the jump at 20 —
        // 20 connection + 10 first-slot = 30.
        expect(priceOf('Sydney 1'), 'Sydney 1 (disconnected, capped)').to.equal(30);
    });

    it('should not count Australia uranium mines toward the 3-power-plant limit', () => {
        const G = setup(5, { map: 'Australia', variant: 'recharged', randomizeMap: false }, 'australia-mine-cap');
        G.phase = Phase.Auction;
        const player = G.players[0];

        // 3 real power plants + 2 mines: still only "3 plants" for the hand limit,
        // so no forced discard is offered.
        player.powerPlants = [
            getPowerPlant(3),
            getPowerPlant(4),
            getPowerPlant(5),
            getPowerPlant(11),
            getPowerPlant(23),
        ];
        expect(availableMoves(G, player)[MoveName.DiscardPowerPlant], '3 plants + 2 mines').to.be.undefined;

        // Sanity: 4 real power plants still trips the limit (mines didn't disable it).
        player.powerPlants = [getPowerPlant(3), getPowerPlant(4), getPowerPlant(5), getPowerPlant(6)];
        const discardable = availableMoves(G, player)[MoveName.DiscardPowerPlant];
        expect(discardable, '4 real plants').to.not.be.undefined;
        // And a mine is never a discard candidate.
        player.powerPlants = [
            getPowerPlant(3),
            getPowerPlant(4),
            getPowerPlant(5),
            getPowerPlant(6),
            getPowerPlant(11),
        ];
        expect(availableMoves(G, player)[MoveName.DiscardPowerPlant]).to.not.include(11);
    });

    it('should not let Australia uranium mines power cities in Bureaucracy', () => {
        const G = setup(5, { map: 'Australia', variant: 'recharged', randomizeMap: false }, 'australia-mine-power');
        G.phase = Phase.Bureaucracy;
        const player = G.players[0];

        // Two mines, fully fuelled — they must still never be offered as a way to
        // power cities (mines produce uranium for sale instead; that is session 3).
        player.powerPlants = [getPowerPlant(11), getPowerPlant(23)];
        player.powerPlantsNotUsed = [11, 23];
        player.uraniumLeft = 10;
        player.uraniumCapacity = 10;

        const moves = availableMoves(G, player);
        expect(moves[MoveName.UsePowerPlant], 'mines offered to power cities').to.be.undefined;
        expect(moves[MoveName.Pass], 'can still pass Bureaucracy').to.not.be.undefined;
    });

    it('should start the Australia uranium-mine market full and only on Australia', () => {
        const G = setup(5, { map: 'Australia', variant: 'recharged', randomizeMap: false }, 'australia-uranium-init');
        expect(G.uraniumMineMarket).to.deep.equal([2, 2, 2, 2, 2, 2]);

        const other = setup(5, { map: 'South Africa', variant: 'recharged', randomizeMap: false }, 'sa-uranium-init');
        expect(other.uraniumMineMarket, 'non-Australia has no uranium-mine market').to.be.undefined;
    });

    it('should pay nothing for Australia uranium while the market is full (round 1)', () => {
        const G = setup(5, { map: 'Australia', variant: 'recharged', randomizeMap: false }, 'australia-uranium-full');
        const player = G.players[0];
        player.money = 0;
        player.powerPlants = [getPowerPlant(11), getPowerPlant(23)]; // mines powering 2 + 3

        const sale = sellUraniumMine(G, player);
        expect(sale.income, 'no empty slot to sell into').to.equal(0);
        expect(sale.mines).to.equal(2);
        expect(player.money).to.equal(0);
        expect(G.uraniumMineMarket).to.deep.equal([2, 2, 2, 2, 2, 2]);
    });

    it('should remove Australia uranium tokens from the cheapest filled slots on resupply', () => {
        const G = setup(5, { map: 'Australia', variant: 'recharged', randomizeMap: false }, 'australia-uranium-remove');
        // Full market: removing 3 empties the $2 column (2 tokens), then one $3 token.
        expect(resupplyUraniumMine(G, 3)).to.equal(3);
        expect(G.uraniumMineMarket).to.deep.equal([0, 1, 2, 2, 2, 2]);

        // Removal is capped by the tokens actually present.
        G.uraniumMineMarket = [0, 0, 0, 0, 0, 1];
        expect(resupplyUraniumMine(G, 5)).to.equal(1);
        expect(G.uraniumMineMarket).to.deep.equal([0, 0, 0, 0, 0, 0]);
    });

    it('should sell Australia uranium at the highest empty price and place one token per mine', () => {
        const G = setup(5, { map: 'Australia', variant: 'recharged', randomizeMap: false }, 'australia-uranium-sell');
        const player = G.players[0];
        player.money = 0;
        // $2 and $3 columns empty, $4–$7 full. Highest empty price is $3.
        G.uraniumMineMarket = [0, 0, 2, 2, 2, 2];
        player.powerPlants = [getPowerPlant(11), getPowerPlant(23)]; // power 2 + 3 = 5 cities

        const sale = sellUraniumMine(G, player);
        expect(sale.price).to.equal(3);
        expect(sale.income, '$3 × 5 cities').to.equal(15);
        expect(player.money).to.equal(15);
        // Two tokens placed on the highest empty slots (both into the $3 column).
        expect(G.uraniumMineMarket).to.deep.equal([0, 2, 2, 2, 2, 2]);
    });

    it('should sell Australia uranium in player order, draining the top price first', () => {
        const G = setup(5, { map: 'Australia', variant: 'recharged', randomizeMap: false }, 'australia-uranium-order');
        // Only one empty slot left, at $7.
        G.uraniumMineMarket = [2, 2, 2, 2, 2, 1];

        const first = G.players[0];
        first.money = 0;
        first.powerPlants = [getPowerPlant(34)]; // powers 5
        const firstSale = sellUraniumMine(G, first);
        expect(firstSale.price, 'first seller takes $7').to.equal(7);
        expect(first.money, '$7 × 5').to.equal(35);
        expect(G.uraniumMineMarket).to.deep.equal([2, 2, 2, 2, 2, 2]); // now full

        const second = G.players[1];
        second.money = 0;
        second.powerPlants = [getPowerPlant(39)]; // powers 6
        const secondSale = sellUraniumMine(G, second);
        expect(secondSale.income, 'market full: later seller earns nothing').to.equal(0);
        expect(second.money).to.equal(0);
    });

    it('should apply the Australia Step 3 CO2 tax by shifting resource prices to $3–$10', () => {
        const G = setup(5, { map: 'Australia', variant: 'recharged', randomizeMap: false }, 'australia-co2');
        const shifted = [3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8, 9, 9, 9, 10, 10, 10];

        expect(G.coalPrices![0], 'standard $1–$8 before Step 3').to.equal(1);

        applyAustraliaStep3Shift(G);
        expect(G.coalPrices).to.deep.equal(shifted);
        expect(G.oilPrices).to.deep.equal(shifted);
        expect(G.garbagePrices).to.deep.equal(shifted);
        // A full coal market now sells its cheapest cube at $3, not $1.
        expect(G.coalPrices![G.coalPrices!.length - G.coalMarket]).to.equal(3);

        // Idempotent: a second call must not double-shift.
        applyAustraliaStep3Shift(G);
        expect(G.coalPrices).to.deep.equal(shifted);

        // Non-Australia maps are untouched.
        const sa = setup(5, { map: 'South Africa', variant: 'recharged', randomizeMap: false }, 'sa-co2');
        applyAustraliaStep3Shift(sa);
        expect(sa.coalPrices![0]).to.equal(1);
    });

    it('should allow invalid move when isUndo is true', () => {
        const game = undo;
        const options: GameOptions = {
            fastBid: game.options.fastBid,
            map: game.options.map as MapName,
            showMoney: game.options.showMoney,
            variant: game.options.variant as Variant,
        };

        let G = setup(game.players.length, options, game.seed, game.knownPowerPlantDeck, game.map);

        for (const item of game.log) {
            if (item.type === 'move') {
                G = move(G, item.move! as Move, item.player!, true);
            }
        }

        expect(ended(G)).to.be.false;
    });

    it('should set Bremen Step 2 and end-game thresholds (and set up) for every player count', () => {
        const step2 = [5, 5, 5, 5, 4];
        const endGame = [13, 13, 13, 12, 11];
        for (let pc = 2; pc <= 6; pc++) {
            const G = setup(
                pc,
                { map: 'Bremen', variant: 'recharged', randomizeMap: false },
                `bremen-thresholds-${pc}`
            );
            expect(G.citiesToStep2, `Bremen ${pc}P Step 2`).to.equal(step2[pc - 2]);
            expect(G.citiesToEndGame, `Bremen ${pc}P end game`).to.equal(endGame[pc - 2]);
            expect(
                G.players.some((p) => p.availableMoves && Object.keys(p.availableMoves).length > 0),
                `Bremen ${pc}P ready`
            ).to.be.true;
        }
    });

    it('should remove the Bremen banned plants (incl. all nuclear) and use no uranium', () => {
        const baseBanned = [11, 17, 23, 28, 34, 36, 38, 39, 46];
        // 2–4P additionally box 31 and 50; check a low and a high player count.
        for (const pc of [2, 5]) {
            const G = setup(pc, { map: 'Bremen', variant: 'recharged', randomizeMap: false }, `bremen-deck-${pc}`);
            const allNumbers = new Set<number>([
                ...G.actualMarket.map((p) => p.number),
                ...G.futureMarket.map((p) => p.number),
                ...G.powerPlantsDeck.map((p) => p.number),
            ]);
            for (const n of baseBanned) {
                expect(allNumbers.has(n), `Bremen ${pc}P: plant ${n} removed`).to.be.false;
            }
            if (pc <= 4) {
                expect(allNumbers.has(31), `Bremen ${pc}P: plant 31 removed`).to.be.false;
                expect(allNumbers.has(50), `Bremen ${pc}P: plant 50 removed`).to.be.false;
            }
            // The opening market is drawn from the ≤15 weak pool.
            expect(
                [...G.actualMarket, ...G.futureMarket].every((p) => p.number <= 15),
                `Bremen ${pc}P: market is weak-pool`
            ).to.be.true;
        }
        // No uranium token is ever in play on Bremen.
        const G = setup(5, { map: 'Bremen', variant: 'recharged', randomizeMap: false }, 'bremen-uranium');
        expect(G.map.startingSupply![3], 'Bremen uranium supply').to.equal(0);
        // The printed track holds only two cubes per resource at $7 and $8,
        // so a full market is 22 cubes and coal starts exactly full.
        for (const track of [G.coalPrices!, G.oilPrices!, G.garbagePrices!]) {
            expect(track, 'Bremen $7/$8 hold two cubes').to.deep.equal([
                1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 8, 8,
            ]);
        }
        expect(G.coalMarket, 'Bremen coal market starts full').to.equal(22);
        expect(G.oilMarket, 'Bremen oil fills $3–$8').to.equal(16);
        expect(G.garbageMarket, 'Bremen garbage fills $3–$8').to.equal(16);
    });

    it('should price Bremen builds by summed district costs (node-weighted, asymmetric)', () => {
        // 5P so all five regions (all 25 districts) are in play.
        const G = setup(5, { map: 'Bremen', variant: 'recharged', randomizeMap: false }, 'bremen-build-cost');
        G.phase = Phase.Building;
        G.step = 1;
        const player = G.players[0];
        player.money = 100;

        // From a network in Seehausen, the rulebook example: connecting Gröpelingen
        // costs 25 — path Seehausen → Höfen (transit, 9) → Gröpelingen (8) = 17 in
        // district costs, plus the first house (8). Höfen itself is a neighbour: 9 + 8.
        player.cities = [{ name: 'Seehausen', position: 0 }];
        let builds = availableMoves(G, player)[MoveName.Build] as { name: string; price: number }[];
        expect(builds.find((b) => b.name === 'Höfen')?.price, 'Seehausen → Höfen').to.equal(17);
        expect(builds.find((b) => b.name === 'Gröpelingen')?.price, 'Seehausen → Gröpelingen (rulebook)').to.equal(25);

        // Asymmetry: from Höfen, connecting Seehausen pays Seehausen's own cost (14) +
        // its first house (8, a small district) = 22, not the 17 of the reverse trip.
        player.cities = [{ name: 'Höfen', position: 0 }];
        builds = availableMoves(G, player)[MoveName.Build] as { name: string; price: number }[];
        expect(builds.find((b) => b.name === 'Seehausen')?.price, 'Höfen → Seehausen (asymmetric)').to.equal(22);
    });

    it('should set Manhattan end-game thresholds, stay in Step 1, and set up for every player count', () => {
        const endGame = [18, 17, 17, 15, 14];
        for (let pc = 2; pc <= 6; pc++) {
            const G = setup(
                pc,
                { map: 'Manhattan', variant: 'recharged', randomizeMap: false },
                `manhattan-thresholds-${pc}`
            );
            expect(G.citiesToEndGame, `Manhattan ${pc}P end game`).to.equal(endGame[pc - 2]);
            expect(G.step, `Manhattan ${pc}P starts in Step 1`).to.equal(1);
            expect(
                G.players.some((p) => p.availableMoves && Object.keys(p.availableMoves).length > 0),
                `Manhattan ${pc}P ready`
            ).to.be.true;
        }
    });

    it('should box the Manhattan Step 3 card + 2–3P plants and keep uranium in play', () => {
        for (const pc of [2, 5]) {
            const G = setup(
                pc,
                { map: 'Manhattan', variant: 'recharged', randomizeMap: false },
                `manhattan-deck-${pc}`
            );
            const allNumbers = new Set<number>([
                ...G.actualMarket.map((p) => p.number),
                ...G.futureMarket.map((p) => p.number),
                ...G.powerPlantsDeck.map((p) => p.number),
            ]);
            // The opening 8-card market is drawn from the ≤15 plug pool.
            expect(
                [...G.actualMarket, ...G.futureMarket].every((p) => p.number <= 15),
                `Manhattan ${pc}P: market is plug-pool`
            ).to.be.true;
            // 2–3 players box plants 20, 22, 37; 4–6 players keep them in the deck.
            for (const n of [20, 22, 37]) {
                expect(allNumbers.has(n), `Manhattan ${pc}P: plant ${n} present?`).to.equal(pc > 3);
            }
        }
        // Manhattan uses uranium (unlike Bremen): the supply is the full 12 cubes.
        const G = setup(5, { map: 'Manhattan', variant: 'recharged', randomizeMap: false }, 'manhattan-uranium');
        expect(G.map.startingSupply![3], 'Manhattan uranium supply').to.equal(12);
    });

    it('should price Manhattan builds by a flat 5 per transited space + the building cost', () => {
        const G = setup(5, { map: 'Manhattan', variant: 'recharged', randomizeMap: false }, 'manhattan-build-cost');
        G.phase = Phase.Building;
        G.step = 1;
        const player = G.players[0];
        player.money = 200;

        // Geometry-agnostic: derive cases from the live map graph so the test holds as
        // the Session-3 board is refined. adj = the street-adjacency of every space.
        const cities = G.map.cities;
        const priceOf = (name: string) => cities.find((c) => c.name === name)!.slotCosts![0];
        const adj: Record<string, string[]> = {};
        for (const c of cities) adj[c.name] = [];
        for (const con of G.map.connections) {
            adj[con.nodes[0]].push(con.nodes[1]);
            adj[con.nodes[1]].push(con.nodes[0]);
        }

        // First house: any empty space costs exactly its own building cost.
        player.cities = [];
        let builds = availableMoves(G, player)[MoveName.Build] as { name: string; price: number }[];
        for (const c of cities) {
            expect(builds.find((b) => b.name === c.name)?.price, `first house ${c.name}`).to.equal(priceOf(c.name));
        }

        // Find A - N0 (adjacent) - C (two hops, not itself adjacent to A).
        let A = '';
        let N0 = '';
        let C = '';
        search: for (const a of cities) {
            for (const n of adj[a.name]) {
                const c = adj[n].find((x) => x !== a.name && !adj[a.name].includes(x));
                if (c) {
                    A = a.name;
                    N0 = n;
                    C = c;
                    break search;
                }
            }
        }
        expect(A, 'found an A-N0-C chain in the board graph').to.not.equal('');

        // From a one-space network at A: every direct neighbour costs only its building
        // cost (adjacent, no transit); the two-hop space C costs its building cost + a
        // single flat-5 transit.
        player.cities = [{ name: A, position: 0 }];
        builds = availableMoves(G, player)[MoveName.Build] as { name: string; price: number }[];
        for (const N of adj[A]) {
            expect(builds.find((b) => b.name === N)?.price, `${A} -> ${N} (adjacent)`).to.equal(priceOf(N));
        }
        expect(builds.find((b) => b.name === C)?.price, `${A} -> ${C} (one transit)`).to.equal(priceOf(C) + 5);

        // One house per space: if another player holds neighbour N0, it drops out.
        G.players[1].cities = [{ name: N0, position: 0 }];
        builds = availableMoves(G, player)[MoveName.Build] as { name: string; price: number }[];
        expect(
            builds.find((b) => b.name === N0),
            `${N0} occupied -> not buildable`
        ).to.be.undefined;
    });

    it('should drive the Manhattan market lifecycle through both deck depletions', () => {
        const mkt = (...nums: number[]): PowerPlant[] => nums.map((n) => getPowerPlant(n));
        const nums = (plants: PowerPlant[]): number[] => plants.map((p) => p.number).sort((a, b) => a - b);
        const base = () =>
            setup(4, { map: 'Manhattan', variant: 'recharged', randomizeMap: false }, 'manhattan-lifecycle');

        // Stage 0: the two highest future-market plants go to the recycle pile (not
        // the box) and the market refills from the deck, staying at eight.
        let G = base();
        G.actualMarket = mkt(3, 4, 5, 6);
        G.futureMarket = mkt(7, 8, 9, 10);
        G.powerPlantsDeck = mkt(11, 12, 13, 14, 15, 16);
        G.manhattanRecyclePile = [];
        G.manhattanDepletion = 0;
        applyManhattanMarketLifecycle(G);
        expect(G.manhattanDepletion, 'stage 0 stays stage 0 while the deck has cards').to.equal(0);
        expect(nums(G.manhattanRecyclePile!), 'two biggest future plants set aside').to.deep.equal([9, 10]);
        expect(G.actualMarket.length + G.futureMarket.length, 'market refilled to 8').to.equal(8);
        expect(G.powerPlantsDeck.length, 'two plants drawn from the deck').to.equal(4);
        expect(
            [...G.actualMarket, ...G.futureMarket].some((p) => p.number === 9 || p.number === 10),
            '9 and 10 are off the market'
        ).to.be.false;

        // First depletion: deck empty + a recycle pile exists → reshuffle the pile
        // into a fresh deck, advance to stage 1, and refill the market.
        G = base();
        G.actualMarket = mkt(3, 4, 5, 6);
        G.futureMarket = mkt(7, 8, 9, 10);
        G.powerPlantsDeck = [];
        G.manhattanRecyclePile = mkt(16, 17, 18);
        G.manhattanDepletion = 0;
        applyManhattanMarketLifecycle(G);
        expect(G.manhattanDepletion, 'first depletion → stage 1').to.equal(1);
        expect(G.manhattanRecyclePile!.length, 'recycle pile emptied into the deck').to.equal(0);
        expect(G.actualMarket.length + G.futureMarket.length, 'market refilled to 8 after reshuffle').to.equal(8);
        // Pile was [16,17,18] + peeled [9,10] = 5 cards; two were drawn to refill.
        expect(G.powerPlantsDeck.length, 'three of the five recycled cards remain').to.equal(3);

        // Stage 1: the single highest future plant rotates to the bottom of the deck.
        G = base();
        G.actualMarket = mkt(3, 4, 5, 6);
        G.futureMarket = mkt(7, 8, 9, 10);
        G.powerPlantsDeck = mkt(20, 21);
        G.manhattanRecyclePile = [];
        G.manhattanDepletion = 1;
        applyManhattanMarketLifecycle(G);
        expect(G.manhattanDepletion, 'stage 1 stays stage 1 while the deck has cards').to.equal(1);
        expect(G.actualMarket.length + G.futureMarket.length, 'market still 8').to.equal(8);
        expect(G.manhattanRecyclePile!.length, 'no recycle pile in stage 1').to.equal(0);
        expect(G.powerPlantsDeck[G.powerPlantsDeck.length - 1].number, 'plant 10 rotated under the deck').to.equal(10);

        // Second depletion: deck empties again → the whole market becomes buyable
        // (everything collapses into the actual market) and we stay in Step 1.
        G = base();
        G.actualMarket = mkt(3, 4, 5);
        G.futureMarket = mkt(8);
        G.powerPlantsDeck = [];
        G.manhattanRecyclePile = [];
        G.manhattanDepletion = 1;
        applyManhattanMarketLifecycle(G);
        expect(G.manhattanDepletion, 'second depletion → stage 2').to.equal(2);
        expect(G.futureMarket.length, 'no future market once all plants are buyable').to.equal(0);
        expect(nums(G.actualMarket), 'every plant is in the buyable market').to.deep.equal([3, 4, 5, 8]);
        expect(G.step, 'Manhattan never advances past Step 1').to.equal(1);

        // Stage 2: each round boxes the single cheapest plant for the endgame churn.
        G = base();
        G.actualMarket = mkt(3, 4, 5, 6, 7, 8);
        G.futureMarket = [];
        G.powerPlantsDeck = [];
        G.manhattanDepletion = 2;
        applyManhattanMarketLifecycle(G);
        expect(G.manhattanDepletion, 'stage 2 is terminal').to.equal(2);
        expect(nums(G.actualMarket), 'smallest plant (3) removed from the game').to.deep.equal([4, 5, 6, 7, 8]);
    });

    it('should block Manhattan spaces by player count, transitable but unbuildable', () => {
        // Per-colour cost-tier plan (mirrors manhattan.ts blockSpaces). 4 players
        // block one colour, 2–3 players block two; 5–6 players block nothing.
        const tierTable: Record<number, number> = { 10: 3, 15: 3, 20: 2, 25: 2, 30: 2, 35: 2 };
        const expectedBlocked = (cities: { slotCosts?: number[] }[], colours: number): number => {
            let total = 0;
            for (const [priceStr, perColour] of Object.entries(tierTable)) {
                const avail = cities.filter((c) => c.slotCosts && c.slotCosts[0] === Number(priceStr)).length;
                total += Math.min(perColour * colours, avail);
            }
            return total;
        };

        // 5–6 players: full board, nothing blocked.
        for (const pc of [5, 6]) {
            const G = setup(
                pc,
                { map: 'Manhattan', variant: 'recharged', randomizeMap: false },
                `manhattan-block-${pc}`
            );
            expect(G.blockedCities ?? [], `Manhattan ${pc}P blocks nothing`).to.deep.equal([]);
        }

        // 2–4 players: the right number per the tier plan, all distinct, never the
        // top (40) tier, and two-colour counts (2–3P) at least the one-colour count.
        const counts: Record<number, number> = {};
        for (const pc of [2, 3, 4]) {
            const G = setup(
                pc,
                { map: 'Manhattan', variant: 'recharged', randomizeMap: false },
                `manhattan-block-${pc}`
            );
            const blocked = G.blockedCities ?? [];
            const colours = pc === 4 ? 1 : 2;
            expect(blocked.length, `Manhattan ${pc}P block count`).to.equal(expectedBlocked(G.map.cities, colours));
            expect(new Set(blocked).size, `Manhattan ${pc}P blocked spaces distinct`).to.equal(blocked.length);
            for (const name of blocked) {
                const cost = G.map.cities.find((c) => c.name === name)!.slotCosts![0];
                expect(cost, `Manhattan ${pc}P never blocks the 40 tier`).to.not.equal(40);
            }
            counts[pc] = blocked.length;
        }
        expect(counts[2], '2–3P (two colours) blocks at least as much as 4P').to.be.greaterThan(counts[4]);
        expect(counts[2], '2P and 3P block the same amount').to.equal(counts[3]);

        // Same seed → same blocked set (deterministic for replay).
        const a = setup(3, { map: 'Manhattan', variant: 'recharged', randomizeMap: false }, 'manhattan-block-det');
        const b = setup(3, { map: 'Manhattan', variant: 'recharged', randomizeMap: false }, 'manhattan-block-det');
        expect(a.blockedCities).to.deep.equal(b.blockedCities);

        // Transitable but unbuildable: blocking a space B makes B unbuildable, yet a
        // space C two hops away - whose only short path runs through B - stays reachable
        // by paying the flat-5 transit through the blocked B. Derived from the graph so
        // it holds as the board is refined.
        const G = setup(5, { map: 'Manhattan', variant: 'recharged', randomizeMap: false }, 'manhattan-block-transit');
        G.phase = Phase.Building;
        G.step = 1;
        const cities = G.map.cities;
        const priceOf = (name: string) => cities.find((c) => c.name === name)!.slotCosts![0];
        const adj: Record<string, string[]> = {};
        for (const c of cities) adj[c.name] = [];
        for (const con of G.map.connections) {
            adj[con.nodes[0]].push(con.nodes[1]);
            adj[con.nodes[1]].push(con.nodes[0]);
        }
        // A-B adjacent; C adjacent to B, not to A, and B is the ONLY one of A's
        // neighbours adjacent to C - so C's cheapest route from A (2 hops, +5) transits B.
        let A = '';
        let B = '';
        let C = '';
        chain: for (const a of cities) {
            for (const b of adj[a.name]) {
                const c = adj[b].find(
                    (x) =>
                        x !== a.name &&
                        !adj[a.name].includes(x) &&
                        adj[a.name].filter((n) => adj[n].includes(x)).length === 1
                );
                if (c) {
                    A = a.name;
                    B = b;
                    C = c;
                    break chain;
                }
            }
        }
        expect(A, 'found an A-B-C chain where B is the only 2-hop connector for C').to.not.equal('');
        G.blockedCities = [B];
        const player = G.players[0];
        player.money = 500;
        player.cities = [{ name: A, position: 0 }];
        const builds = availableMoves(G, player)[MoveName.Build] as { name: string; price: number }[];
        expect(
            builds.find((b) => b.name === B),
            `blocked ${B} is unbuildable`
        ).to.be.undefined;
        expect(builds.find((b) => b.name === C)?.price, `${C} reachable transiting blocked ${B}`).to.equal(
            priceOf(C) + 5
        );
    });

    it('should grant a Manhattan discount buyer another purchase this phase (declinable in round 1)', () => {
        let G = setup(2, { map: 'Manhattan', variant: 'recharged', randomizeMap: false }, 'manhattan-discount-bonus');
        expect(G.phase, 'starts in Auction').to.equal(Phase.Auction);
        expect(G.round, 'round 1').to.equal(1);
        expect(G.plantDiscountActive, 'discount active at setup').to.be.true;

        const buyer = G.currentPlayers[0];
        const other = G.players.find((p) => p.id !== buyer)!.id;
        const discounted = G.actualMarket[0].number;

        // Take the discounted plant: choose it, open at the discount floor of 1,
        // the other player passes the bid -> buyer wins it for 1.
        G = move(G, { name: MoveName.ChoosePowerPlant, data: discounted } as Move, buyer);
        G = move(G, { name: MoveName.Bid, data: 1 } as Move, buyer);
        G = move(G, { name: MoveName.Pass, data: true } as Move, other);

        expect(
            G.players[buyer].powerPlants.map((p) => p.number),
            'buyer got the discounted plant'
        ).to.include(discounted);
        // Buyer is owed the bonus purchase and is NOT yet done with the auction.
        expect(G.discountBonusPlayer, 'buyer owed the bonus').to.equal(buyer);
        expect(G.players[buyer].skipAuction, 'buyer still eligible').to.be.false;
        expect(G.currentPlayers[0], 'buyer acts again').to.equal(buyer);

        // The fix: round 1 normally forces a buy, but the bonus buyer may decline AND
        // may buy another plant.
        const bonusMoves = availableMoves(G, G.players[buyer]);
        expect(bonusMoves[MoveName.Pass], 'bonus is declinable even in round 1').to.not.be.undefined;
        expect(bonusMoves[MoveName.ChoosePowerPlant], 'bonus buyer may buy another plant').to.not.be.undefined;

        // Decline it: buyer is now done, flag clears, the auction moves to the other player.
        G = move(G, { name: MoveName.Pass, data: true } as Move, buyer);
        expect(G.discountBonusPlayer, 'flag cleared on decline').to.be.undefined;
        expect(G.players[buyer].skipAuction, 'buyer done after declining').to.be.true;
        expect(G.currentPlayers[0], 'other player must still buy (round 1)').to.equal(other);
    });

    it('should NOT grant a bonus purchase for a non-discounted Manhattan buy', () => {
        let G = setup(2, { map: 'Manhattan', variant: 'recharged', randomizeMap: false }, 'manhattan-no-bonus');
        const buyer = G.currentPlayers[0];
        const other = G.players.find((p) => p.id !== buyer)!.id;
        // Choose a plant that is NOT the cheapest -> no discount applies.
        const plant = G.actualMarket[1].number;

        G = move(G, { name: MoveName.ChoosePowerPlant, data: plant } as Move, buyer);
        G = move(G, { name: MoveName.Bid, data: plant } as Move, buyer);
        G = move(G, { name: MoveName.Pass, data: true } as Move, other);

        expect(
            G.players[buyer].powerPlants.map((p) => p.number),
            'buyer got the chosen plant'
        ).to.include(plant);
        expect(G.discountBonusPlayer, 'no bonus for a non-discounted buy').to.be.undefined;
        expect(G.players[buyer].skipAuction, 'buyer done after a normal buy').to.be.true;
    });

    it('should not grow the Manhattan market when a discount-bonus buy forces a discard', () => {
        let G = setup(2, { map: 'Manhattan', variant: 'recharged', randomizeMap: false }, 'manhattan-overcap-bonus');
        // Put player 0 at the 2P plant cap (4) with high plants that are NOT in the
        // opening market, and make it their uncontested turn with the discount live.
        // Buying the discounted plant pushes them to 5 -> forced discard.
        const p0 = G.players[0];
        p0.money = 100;
        p0.powerPlants = [getPowerPlant(42), getPowerPlant(44), getPowerPlant(46), getPowerPlant(50)];
        G.players[1].skipAuction = true;
        G.plantDiscountActive = true;
        G.round = 2;
        G.currentPlayers = [0];
        G.chosenPowerPlant = undefined;

        const before = G.actualMarket.length + G.futureMarket.length;
        const discounted = G.actualMarket[0].number;
        G = move(G, { name: MoveName.ChoosePowerPlant, data: discounted } as Move, 0);

        // Over the cap now -> must discard; the bonus is still owed.
        expect(G.discountBonusPlayer, 'still owed the bonus after the discount buy').to.equal(0);
        const discardable = (availableMoves(G, G.players[0])[MoveName.DiscardPowerPlant] ?? []) as number[];
        expect(discardable.length, 'over the cap -> must discard a plant').to.be.greaterThan(0);

        G = move(G, { name: MoveName.DiscardPowerPlant, data: discardable[0] } as Move, 0);

        // The market must NOT have grown: one plant bought + one refilled = net zero.
        // (Regression: the bonus branch used to refill here AND in the discard handler.)
        expect(G.actualMarket.length + G.futureMarket.length, 'market unchanged by buy+discard').to.equal(before);
        expect(G.discountBonusPlayer, 'bonus still owed after discarding').to.equal(0);
    });

    it('should limit Bremen small districts to two networks', () => {
        const G = setup(5, { map: 'Bremen', variant: 'recharged', randomizeMap: false }, 'bremen-small-cap');
        G.phase = Phase.Building;
        G.step = 3; // 3 slots open by step, so only the small district's own 2-slot limit binds
        const player = G.players[0];
        player.money = 100;
        player.cities = [{ name: 'Walle', position: 0 }];
        // Two other players already occupy Findorff (small, 2 slots) and Mitte (full, 3).
        G.players[1].cities = [
            { name: 'Findorff', position: 1 },
            { name: 'Mitte', position: 1 },
        ];
        G.players[2].cities = [
            { name: 'Findorff', position: 2 },
            { name: 'Mitte', position: 2 },
        ];

        const builds = availableMoves(G, player)[MoveName.Build] as { name: string; price: number }[];
        const priceOf = (name: string) => builds.find((b) => b.name === name)?.price;
        // Findorff is full at two networks — no third slot for this player.
        expect(priceOf('Findorff') === undefined || priceOf('Findorff') === 9999, 'Findorff small, full').to.be.true;
        // Mitte still has its third slot (20): connection 1 + 20 = 21.
        expect(priceOf('Mitte'), 'Mitte third slot').to.equal(21);
    });

    it('should draft regions when chooseRegions is set, then start the auction', () => {
        const numPlayers = 5;
        const G0 = setup(numPlayers, { map: 'Germany', chooseRegions: true, fastBid: false }, 'cr-seed');

        // Setup enters the draft holding the FULL map; nothing filtered yet.
        const allRegions = new Set(G0.map.cities.map((c) => c.region));
        const regionsNeeded = G0.regionDraft!.regionsNeeded;
        expect(G0.phase).to.equal(Phase.RegionSelection);
        expect(regionsNeeded).to.equal(5); // 5 players use 5 regions
        expect(allRegions.size).to.be.greaterThan(regionsNeeded); // otherwise no real choice
        expect(G0.currentPlayers).to.deep.equal([0]);

        // The first picker may choose any region.
        const firstMoves = G0.players[0].availableMoves![MoveName.ChooseRegion]!;
        expect(new Set(firstMoves)).to.deep.equal(allRegions);

        // Drive the draft: each current player picks the first legal region.
        let G = G0;
        const picks: string[] = [];
        const pickOrder: number[] = [];
        while (G.phase === Phase.RegionSelection) {
            const picker = G.currentPlayers[0];
            pickOrder.push(picker);
            const options = G.players[picker].availableMoves![MoveName.ChooseRegion]!;
            expect(options.length, 'the current picker always has at least one legal region').to.be.greaterThan(0);
            const region = options[0];
            picks.push(region);
            G = move(G, { name: MoveName.ChooseRegion, data: region } as Move, picker);
        }

        // Draft completed straight into the auction.
        expect(G.phase).to.equal(Phase.Auction);
        expect(G.regionDraft).to.be.undefined;
        expect(picks.length).to.equal(regionsNeeded);

        // Players picked in seating order (5 regions, 5 players -> one each).
        expect(pickOrder).to.deep.equal([0, 1, 2, 3, 4]);

        // Map filtered to exactly the picked regions, and every kept connection lies
        // entirely within them.
        const finalRegions = new Set(G.map.cities.map((c) => c.region));
        expect(finalRegions).to.deep.equal(new Set(picks));
        const cityRegion = new Map(G.map.cities.map((c) => [c.name, c.region]));
        for (const con of G.map.connections) {
            for (const node of con.nodes) {
                expect(finalRegions.has(cityRegion.get(node)!), node).to.be.true;
            }
        }

        // The game is playable: the starting player can act in the auction.
        expect(G.currentPlayers).to.deep.equal([0]);
        expect(G.players[0].availableMoves![MoveName.ChoosePowerPlant]).to.exist;
    });

    it('should draft in seating order, wrapping for 2 players (chooseRegions)', () => {
        const G0 = setup(2, { map: 'Germany', chooseRegions: true, fastBid: false }, 'cr-2p');
        expect(G0.regionDraft!.regionsNeeded).to.equal(3); // 2 players use 3 regions

        let G = G0;
        const pickOrder: number[] = [];
        while (G.phase === Phase.RegionSelection) {
            const picker = G.currentPlayers[0];
            pickOrder.push(picker);
            const region = G.players[picker].availableMoves![MoveName.ChooseRegion]![0];
            G = move(G, { name: MoveName.ChooseRegion, data: region } as Move, picker);
        }

        // First player, second player, then first player again.
        expect(pickOrder).to.deep.equal([0, 1, 0]);
        expect(G.phase).to.equal(Phase.Auction);
        expect(new Set(G.map.cities.map((c) => c.region)).size).to.equal(3);
    });

    it('should restrict region picks to connected regions (chooseRegions)', () => {
        const G0 = setup(3, { map: 'Germany', chooseRegions: true, fastBid: false }, 'cr-seed2');
        expect(G0.phase).to.equal(Phase.RegionSelection);

        // Player 0 picks one region.
        const firstRegion = G0.players[0].availableMoves![MoveName.ChooseRegion]![0];
        const G1 = move(G0, { name: MoveName.ChooseRegion, data: firstRegion } as Move, 0);

        // Player 1's options exclude the picked region and are all legally connected
        // (Germany has no UK/Australia exception).
        const options = G1.players[1].availableMoves![MoveName.ChooseRegion]!;
        expect(options.length).to.be.greaterThan(0);
        expect(options).to.not.include(firstRegion);
        const graph = computeRegionGraph(G1.map);
        for (const region of options) {
            expect(regionPickable('Germany', graph, [firstRegion], region), region).to.be.true;
        }
    });

    it('should replay a chooseRegions draft deterministically', () => {
        const opts: GameOptions = { map: 'Germany', chooseRegions: true, fastBid: false };
        const seed = 'cr-replay';

        // Play the draft, recording each pick.
        let G = setup(4, opts, seed);
        const draftMoves: { player: number; data: string }[] = [];
        while (G.phase === Phase.RegionSelection) {
            const picker = G.currentPlayers[0];
            const region = G.players[picker].availableMoves![MoveName.ChooseRegion]![0];
            draftMoves.push({ player: picker, data: region });
            G = move(G, { name: MoveName.ChooseRegion, data: region } as Move, picker);
        }

        // Re-run setup with the same seed and replay the recorded picks.
        let G2 = setup(4, opts, seed);
        for (const m of draftMoves) {
            G2 = move(G2, { name: MoveName.ChooseRegion, data: m.data } as Move, m.player);
        }

        expect(G2.phase).to.equal(Phase.Auction);
        expect(G2.map.cities.map((c) => c.name).sort()).to.deep.equal(G.map.cities.map((c) => c.name).sort());
    });

    it('should keep the Japan free jump available even when owned cities span multiple network components', () => {
        // 5 players so all five Japan regions are in play (Sapporo sits in Brown).
        const G = setup(5, { map: 'Japan', variant: 'recharged', randomizeMap: false }, 'japan-free-jump');
        G.phase = Phase.Building;
        G.step = 1;
        G.round = 3; // any round past the first, where the free jump becomes a choice
        const player = G.players[0];
        player.money = 100;
        player.usedFreeJump = false;
        // Yokohama and Kofu connect only THROUGH unowned cities (Tokyo, Saitama), so
        // countNetworks() sees two components — the exact shape that used to wrongly hide
        // the free jump even though the player never spent it.
        player.cities = [
            { name: 'Yokohama', position: 0 },
            { name: 'Kofu', position: 0 },
        ];

        const builds = availableMoves(G, player)[MoveName.Build] as {
            name: string;
            price: number;
            freeJump?: boolean;
        }[];
        const sapporoJump = builds.find((b) => b.name === 'Sapporo' && b.freeJump === true);
        expect(sapporoJump, 'Sapporo offered as a free jump').to.not.be.undefined;
        expect(sapporoJump!.price, 'free jump pays the slot cost only (10 in Step 1)').to.equal(10);
    });

    it('should stop offering the Japan free jump once it has been spent', () => {
        const G = setup(5, { map: 'Japan', variant: 'recharged', randomizeMap: false }, 'japan-free-jump-used');
        G.phase = Phase.Building;
        G.step = 1;
        G.round = 3;
        const player = G.players[0];
        player.money = 100;
        player.usedFreeJump = true;
        player.cities = [
            { name: 'Yokohama', position: 0 },
            { name: 'Kofu', position: 0 },
        ];

        const builds = availableMoves(G, player)[MoveName.Build] as {
            name: string;
            price: number;
            freeJump?: boolean;
        }[];
        expect(
            builds.some((b) => b.freeJump === true),
            'no free-jump entries after the jump is used'
        ).to.be.false;
    });

    it('should restrict the Japan first house to a starting city even when the player skipped round 1', () => {
        // Player builds nothing in round 1; in round 2 their first house must still be
        // one of the six starting cities (the cities.length===0 rule is not round-gated).
        const G = setup(5, { map: 'Japan', variant: 'recharged', randomizeMap: false }, 'japan-skip-r1');
        G.phase = Phase.Building;
        G.step = 1;
        G.round = 2;
        const player = G.players[0];
        player.money = 100;
        player.usedFreeJump = false;
        player.cities = [];

        const builds = availableMoves(G, player)[MoveName.Build] as {
            name: string;
            price: number;
            freeJump?: boolean;
        }[];
        expect(builds.map((b) => b.name).sort(), 'only the six starting cities are offered').to.deep.equal(
            ['Fukuoka', 'Kobe', 'Osaka', 'Sapporo', 'Tokyo', 'Yokohama'].sort()
        );
        expect(
            builds.every((b) => b.freeJump !== true),
            'the initial placement is never a free jump'
        ).to.be.true;
    });

    it('should keep then spend the Japan free jump for a player who skipped round 1', () => {
        const G = setup(5, { map: 'Japan', variant: 'recharged', randomizeMap: false }, 'japan-skip-r1-jump');
        G.phase = Phase.Building;
        G.step = 1;
        G.round = 2;
        const player = G.players[0];
        player.money = 100;
        player.usedFreeJump = false;
        player.cities = [];

        // Initial placement in round 2 — must NOT consume the jump.
        G.currentPlayers = [0];
        player.availableMoves = availableMoves(G, player);
        const tokyo = (player.availableMoves[MoveName.Build] as { name: string; price: number }[]).find(
            (b) => b.name === 'Tokyo'
        )!;
        move(G, { name: MoveName.Build, data: tokyo }, 0);
        expect(player.usedFreeJump, 'initial placement keeps the jump').to.be.false;

        // Second build offers the jump into another starting city.
        player.availableMoves = availableMoves(G, player);
        const osaka = (
            player.availableMoves[MoveName.Build] as { name: string; price: number; freeJump?: boolean }[]
        ).find((b) => b.name === 'Osaka' && b.freeJump === true)!;
        expect(osaka, 'free jump offered for the second build').to.not.be.undefined;
        move(G, { name: MoveName.Build, data: osaka }, 0);
        expect(player.usedFreeJump, 'jump consumed on the free-jump build').to.be.true;
    });

    it('should cap Japan round 1 at two houses (initial placement plus the free jump)', () => {
        const G = setup(5, { map: 'Japan', variant: 'recharged', randomizeMap: false }, 'japan-r1-cap');
        G.phase = Phase.Building;
        G.step = 1;
        G.round = 1;
        const player = G.players[0];
        player.money = 100;
        player.usedFreeJump = false;
        player.cities = [];

        // House 1 (initial placement) and house 2 (auto free jump).
        G.currentPlayers = [0];
        player.availableMoves = availableMoves(G, player);
        const h1 = (player.availableMoves[MoveName.Build] as { name: string; price: number }[]).find(
            (b) => b.name === 'Tokyo'
        )!;
        move(G, { name: MoveName.Build, data: h1 }, 0);
        player.availableMoves = availableMoves(G, player);
        const h2 = (player.availableMoves[MoveName.Build] as { name: string; price: number }[]).find(
            (b) => b.name === 'Osaka'
        )!;
        move(G, { name: MoveName.Build, data: h2 }, 0);
        expect(player.usedFreeJump, 'second round-1 build consumes the jump').to.be.true;

        // No third build may be offered in round 1 — the jump is spent.
        const builds3 = availableMoves(G, player)[MoveName.Build];
        expect(builds3, 'no further builds offered in round 1 after the jump is spent').to.be.undefined;
    });

    it('should draft player colors when chooseColors is set, then start the auction', () => {
        const numPlayers = 4;
        const G0 = setup(numPlayers, { map: 'Germany', chooseColors: true, fastBid: false }, 'cc-seed');

        expect(G0.phase).to.equal(Phase.ColorSelection);
        expect(G0.colorDraft!.picked).to.deep.equal([]);
        expect(G0.currentPlayers).to.deep.equal([0]);

        // The first picker sees the full palette.
        const firstOptions = G0.players[0].availableMoves![MoveName.ChooseColor]!;
        expect(firstOptions.length).to.equal(6);

        let G = G0;
        const pickOrder: number[] = [];
        const picks: string[] = [];
        while (G.phase === Phase.ColorSelection) {
            const picker = G.currentPlayers[0];
            pickOrder.push(picker);
            const options = G.players[picker].availableMoves![MoveName.ChooseColor]!;
            // Already-taken colors are never offered again.
            for (const taken of picks) expect(options).to.not.include(taken);
            const color = options[0];
            picks.push(color);
            G = move(G, { name: MoveName.ChooseColor, data: color } as Move, picker);
        }

        // Each player picked exactly once, in seating order.
        expect(pickOrder).to.deep.equal([0, 1, 2, 3]);
        // Colors recorded per player and all distinct.
        expect(G.players.map((p) => p.color)).to.deep.equal(picks);
        expect(new Set(picks).size).to.equal(numPlayers);

        // No region draft -> straight into a playable auction.
        expect(G.phase).to.equal(Phase.Auction);
        expect(G.colorDraft).to.be.undefined;
        expect(G.currentPlayers).to.deep.equal([0]);
        expect(G.players[0].availableMoves![MoveName.ChoosePowerPlant]).to.exist;
    });

    it('should leave colors unset and skip the color draft by default', () => {
        const G = setup(4, { map: 'Germany', fastBid: false }, 'cc-default');
        expect(G.phase).to.equal(Phase.Auction);
        expect(G.colorDraft).to.be.undefined;
        expect(G.players.every((p) => p.color === undefined)).to.be.true;
    });

    it('should run the color draft before the region draft when both options are set', () => {
        const G0 = setup(3, { map: 'Germany', chooseColors: true, chooseRegions: true, fastBid: false }, 'cc-cr');
        expect(G0.phase).to.equal(Phase.ColorSelection);
        expect(G0.regionDraft, 'region draft is pending but inactive during the color draft').to.exist;
        // Capture before play — move() mutates in place, so the draft clears this later.
        const regionsNeeded = G0.regionDraft!.regionsNeeded;
        const allRegions = new Set(G0.map.cities.map((c) => c.region));

        let G = G0;
        // Colors first.
        while (G.phase === Phase.ColorSelection) {
            const picker = G.currentPlayers[0];
            const color = G.players[picker].availableMoves![MoveName.ChooseColor]![0];
            G = move(G, { name: MoveName.ChooseColor, data: color } as Move, picker);
        }

        // Color draft hands off to the region draft, full map still intact.
        expect(G.phase).to.equal(Phase.RegionSelection);
        expect(G.players.every((p) => !!p.color)).to.be.true;
        expect(new Set(G.map.cities.map((c) => c.region))).to.deep.equal(allRegions);

        // Regions next.
        while (G.phase === Phase.RegionSelection) {
            const picker = G.currentPlayers[0];
            const region = G.players[picker].availableMoves![MoveName.ChooseRegion]![0];
            G = move(G, { name: MoveName.ChooseRegion, data: region } as Move, picker);
        }

        expect(G.phase).to.equal(Phase.Auction);
        expect(new Set(G.map.cities.map((c) => c.region)).size).to.equal(regionsNeeded);
        expect(G.players.every((p) => !!p.color)).to.be.true;
    });

    it('should reorder players by plants after a contested round 1 auction (Manhattan)', () => {
        // Regression (reported on ManhattanJune28): round-1 player order is set by the
        // plants bought, but the reorder used to live only in the uncontested
        // ChoosePowerPlant branch. Manhattan's discount-bonus purchase lets round 1
        // finish via the contested/bonus completion path, which skipped the reorder
        // and left the seating order [0,1,2,3,4]. This deterministic auction ends
        // round 1 through that path; the reorder now happens in toResourcesPhase, the
        // single funnel into the resources phase, so it always runs.
        const moves: { player: number; move: Move }[] = [
            { player: 0, move: { name: MoveName.ChoosePowerPlant, data: 3 } },
            { player: 0, move: { name: MoveName.Bid, data: 1 } },
            { player: 1, move: { name: MoveName.Pass, data: true } },
            { player: 2, move: { name: MoveName.Bid, data: 2 } },
            { player: 3, move: { name: MoveName.Bid, data: 3 } },
            { player: 4, move: { name: MoveName.Pass, data: true } },
            { player: 0, move: { name: MoveName.Pass, data: true } },
            { player: 2, move: { name: MoveName.Bid, data: 4 } },
            { player: 3, move: { name: MoveName.Bid, data: 5 } },
            { player: 2, move: { name: MoveName.Pass, data: true } },
            { player: 0, move: { name: MoveName.ChoosePowerPlant, data: 8 } },
            { player: 0, move: { name: MoveName.Bid, data: 8 } },
            { player: 1, move: { name: MoveName.Pass, data: true } },
            { player: 2, move: { name: MoveName.Pass, data: true } },
            { player: 3, move: { name: MoveName.Bid, data: 9 } },
            { player: 4, move: { name: MoveName.Bid, data: 10 } },
            { player: 0, move: { name: MoveName.Pass, data: true } },
            { player: 3, move: { name: MoveName.Bid, data: 11 } },
            { player: 4, move: { name: MoveName.Bid, data: 12 } },
            { player: 3, move: { name: MoveName.Pass, data: true } },
            { player: 0, move: { name: MoveName.ChoosePowerPlant, data: 9 } },
            { player: 0, move: { name: MoveName.Bid, data: 9 } },
            { player: 1, move: { name: MoveName.Bid, data: 10 } },
            { player: 2, move: { name: MoveName.Pass, data: true } },
            { player: 3, move: { name: MoveName.Pass, data: true } },
            { player: 0, move: { name: MoveName.Pass, data: true } },
            { player: 0, move: { name: MoveName.ChoosePowerPlant, data: 7 } },
            { player: 0, move: { name: MoveName.Bid, data: 7 } },
            { player: 2, move: { name: MoveName.Pass, data: true } },
            { player: 3, move: { name: MoveName.Bid, data: 8 } },
            { player: 0, move: { name: MoveName.Bid, data: 9 } },
            { player: 3, move: { name: MoveName.Pass, data: true } },
            { player: 2, move: { name: MoveName.ChoosePowerPlant, data: 10 } },
            { player: 2, move: { name: MoveName.Bid, data: 10 } },
            { player: 3, move: { name: MoveName.Bid, data: 11 } },
            { player: 2, move: { name: MoveName.Bid, data: 12 } },
            { player: 3, move: { name: MoveName.Pass, data: true } },
            { player: 3, move: { name: MoveName.Pass, data: true } },
        ];

        let G = setup(5, { map: 'Manhattan', variant: 'recharged' }, 'cap1');
        for (const m of moves) {
            if (G.phase !== Phase.Auction) break;
            G = move(G, m.move as Move, m.player);
        }

        expect(G.phase).to.equal(Phase.Resources);

        // Round 1: no cities yet, so player order must be by largest plant descending
        // — never the untouched seating order.
        const largestPlant = G.playerOrder.map((id) => Math.max(...G.players[id].powerPlants.map((p) => p.number), -1));
        expect(largestPlant).to.deep.equal([...largestPlant].sort((a, b) => b - a));
        expect(G.playerOrder).to.not.deep.equal([0, 1, 2, 3, 4]);
        expect(G.playerOrder).to.deep.equal([2, 1, 4, 0, 3]);
    });
});
