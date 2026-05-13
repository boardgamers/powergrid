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
