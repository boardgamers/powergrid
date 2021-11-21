import { expect } from 'chai';
import { ended, move, setup } from './engine';
import GermanyRecharged from './fixtures/GermanyRecharged.json';
import USAOriginal from './fixtures/USAOriginal.json';
import { GameOptions, MapName, Variant } from './gamestate';
import { Move } from './move';

describe('Engine', () => {
    it('should setup a game correctly', () => {
        const G = setup(5, { fastBid: false }, 'test');

        // expect(G.factoriesLeft[0].id).to.equal('F1');
        // expect(G.factoriesLeft).to.have.length(20);
        // expect(G.players[0].factories[0].id).to.equal('F5');
        // expect(G.players[1].factories[0].id).to.equal('F15');
        // expect(G.players[2].factories[0].id).to.equal('F10');
        // expect(G.players[3].factories[0].id).to.equal('F20');
        // expect(G.players[4].factories[0].id).to.equal('F0');
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
});
