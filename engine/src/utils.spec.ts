import { expect } from 'chai';
import { minBy, shuffle } from './utils';

describe('utils', () => {
    describe('shuffle', () => {
        it('should shuffle the same way based on the seed', () => {
            expect(shuffle([1, 2, 3, 4], 'a')).to.have.ordered.members([4, 2, 3, 1]);
            expect(shuffle([1, 2, 3, 4], 'b')).to.have.ordered.members([3, 1, 2, 4]);
            expect(shuffle([1, 2, 3, 4], 'b')).to.have.ordered.members([3, 1, 2, 4]);
            expect(shuffle([1, 2, 3, 4], 'a')).to.have.ordered.members([4, 2, 3, 1]);
        });
    });

    describe('minBy', () => {
        it('returns the element with the smallest key', () => {
            expect(minBy([{ p: 3 }, { p: 1 }, { p: 2 }], (x) => x.p)).to.deep.equal({ p: 1 });
        });

        it('breaks ties by returning the earlier element', () => {
            const a = { id: 'a', p: 1 };
            const b = { id: 'b', p: 1 };
            expect(minBy([a, b], (x) => x.p)).to.equal(a);
        });

        it('returns undefined for an empty array', () => {
            expect(minBy([], (x: number) => x)).to.equal(undefined);
        });
    });
});
