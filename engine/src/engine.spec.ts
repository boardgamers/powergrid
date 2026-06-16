import { expect } from 'chai';
import 'mocha';
import { availableMoves } from './available-moves';
import { applyAustraliaStep3Shift, ended, getPowerPlant, move, reconstructState, setup } from './engine';
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
});
