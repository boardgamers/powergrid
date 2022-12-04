import { expect } from 'chai';
import { rankings } from '../wrapper';
import { GameState } from './gamestate';

describe('rankings', () => {
    it('should rank players correctly', () => {
        const players: any[] = [
            { id: 0, citiesPowered: 20, money: 30, cities: { length: 21 } },
            { id: 1, citiesPowered: 20, money: 20, cities: { length: 21 } },
            { id: 2, citiesPowered: 20, money: 30, cities: { length: 21 } },
            { id: 4, citiesPowered: 18, money: 30, cities: { length: 21 } },
            { id: 3, citiesPowered: 18, money: 30, cities: { length: 20 } },
            { id: 5, citiesPowered: 19, money: 30, cities: { length: 21 } },
        ];

        expect(rankings({ players } as GameState)).to.have.ordered.members([1, 3, 1, 5, 6, 4]);
    });
});
