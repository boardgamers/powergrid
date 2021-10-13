import { expect } from 'chai';
import { shuffle } from './utils';

describe('utils', () => {
    describe('shuffle', () => {
        it('should shuffle the same way based on the seed', () => {
            expect(shuffle([1, 2, 3, 4], 'a')).to.have.ordered.members([4, 2, 3, 1]);
            expect(shuffle([1, 2, 3, 4], 'b')).to.have.ordered.members([3, 1, 2, 4]);
            expect(shuffle([1, 2, 3, 4], 'b')).to.have.ordered.members([3, 1, 2, 4]);
            expect(shuffle([1, 2, 3, 4], 'a')).to.have.ordered.members([4, 2, 3, 1]);
        });
    });
});
