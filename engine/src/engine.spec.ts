import { expect } from 'chai';
import 'mocha';
import { ended, move, reconstructState, setup } from './engine';
import GermanyRecharged from './fixtures/GermanyRecharged.json';
import supply from './fixtures/supply.json';
import undo from './fixtures/undo.json';
import USAOriginal from './fixtures/USAOriginal.json';
import { GameOptions, MapName, Variant } from './gamestate';
import { Move } from './move';

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
