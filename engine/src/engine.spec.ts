import { expect } from 'chai';
import 'mocha';
import { availableMoves } from './available-moves';
import { ended, getPowerPlant, move, reconstructState, setup } from './engine';
import GermanyRecharged from './fixtures/GermanyRecharged.json';
import supply from './fixtures/supply.json';
import undo from './fixtures/undo.json';
import USAOriginal from './fixtures/USAOriginal.json';
import { GameOptions, MapName, PowerPlant, PowerPlantType, Variant } from './gamestate';
import { Move, MoveName } from './move';

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

    it('should reduce Europe deck for low player counts', () => {
        // Mike's feedback: in 2P the rules call for 2 plug + 6 normal cards removed
        // (8 total). Engine had no reduction for Europe, leaving a too-large deck
        // at low player counts. Standard PG: 2/3P remove 8, 4P remove 4, 5+P none.
        // Total plants = 42 normal + step3. Initial market draw is 9 (4 actual + 5
        // future). Step 3 buried at bottom of deck. So deck length after setup:
        //   2/3P: 42 - 9 - 8 = 25, plus step3 = 26
        //   4P:   42 - 9 - 4 = 29, plus step3 = 30
        //   5+P:  42 - 9     = 33, plus step3 = 34
        const expected: Record<number, number> = { 2: 26, 3: 26, 4: 30, 5: 34, 6: 34 };
        for (const numPlayers of [2, 3, 4, 5, 6]) {
            const G = setup(
                numPlayers,
                { map: 'Europe', variant: 'recharged', randomizeMap: false },
                `eu-trim-${numPlayers}p`
            );
            expect(G.powerPlantsDeck.length, `Europe ${numPlayers}P deck size`).to.equal(expected[numPlayers]);
            expect(G.actualMarket.length).to.equal(4);
            expect(G.futureMarket.length).to.equal(5);
            // Step 3 is the last card in the deck.
            expect(G.powerPlantsDeck[G.powerPlantsDeck.length - 1].type).to.equal(PowerPlantType.Step3);
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
});
