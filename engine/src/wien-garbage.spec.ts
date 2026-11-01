import { expect } from 'chai';
import { garbagePrice } from './available-moves';
import { reconstructionOptions, setup } from './engine';
import { GameState } from './gamestate';
import { LogItem } from './log';
import { MoveName } from './move';

const withWien = (G: GameState, seat: number) => {
    G.players[seat].cities.push({ name: 'Wien', price: 10 } as never);
    return G;
};

const buyLog = (price: number): LogItem => ({
    type: 'move',
    player: 0,
    move: { name: MoveName.BuyResource, data: { resource: 'garbage' } } as never,
    simple: `Someone buys garbage for $${price}.`,
    pretty: '',
});

describe('Wien garbage discount', () => {
    for (const variant of ['original', 'recharged'] as const) {
        it(`is $1 off but never below $1 in Central Europe ${variant}`, () => {
            const G = withWien(setup(4, { map: 'Central Europe', variant }, 'wien'), 0);

            expect(garbagePrice(G, G.players[0], 1)).to.equal(1);
            expect(garbagePrice(G, G.players[0], 2)).to.equal(1);
            expect(garbagePrice(G, G.players[0], 5)).to.equal(4);
            // Players without Wien pay the printed price.
            expect(garbagePrice(G, G.players[1], 1)).to.equal(1);
            expect(garbagePrice(G, G.players[1], 5)).to.equal(5);
        });
    }

    it('only applies in Central Europe', () => {
        const G = withWien(setup(4, { map: 'Europe', variant: 'original' }, 'wien'), 0);
        expect(garbagePrice(G, G.players[0], 5)).to.equal(5);
    });

    it('keeps the old $0 price for games whose log already shows one', () => {
        const options = setup(4, { map: 'Central Europe', variant: 'original' }, 'wien').options;
        expect(options).to.not.have.property('wienFreeGarbage');

        expect(reconstructionOptions(options, [buyLog(1), buyLog(2)])).to.not.have.property('wienFreeGarbage');
        expect(reconstructionOptions(options, [buyLog(10)])).to.not.have.property('wienFreeGarbage');

        const legacy = reconstructionOptions(options, [buyLog(2), buyLog(0)]);
        expect(legacy.wienFreeGarbage).to.equal(true);

        const G = withWien(setup(4, legacy, 'wien'), 0);
        expect(G.options.wienFreeGarbage).to.equal(true);
        expect(garbagePrice(G, G.players[0], 1)).to.equal(0);
    });
});
