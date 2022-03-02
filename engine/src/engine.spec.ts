import { expect } from 'chai';
import { ended, move, reconstructState, setup } from './engine';
import france from './fixtures/france.json';
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

    it('should replay game Germany recharged', () => {
        const game = GermanyRecharged;

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

    it('should replay game france', () => {
        const game = france;

        const G = reconstructState(game as any, game.log.length - 1);

        expect(ended(G)).to.be.false;
    });
});
