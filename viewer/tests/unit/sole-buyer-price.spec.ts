import Game from '@/components/Game.vue';
import { expect } from 'chai';

const options = (Game as any).options;
const price = (number: number, { variant = 'recharged', discount = false, cheapest = 3 } = {}) =>
    options.methods.soleBuyerPrice.call({
        soleBuyerPlant: { number },
        G: { options: { variant }, plantDiscountActive: discount, actualMarket: [{ number: cheapest }] },
    });

describe('sole buyer price', () => {
    it('charges the printed number for the shuffled decks’ extra copies', () => {
        expect(price(13.1)).to.equal(13);
        expect(price(7.2)).to.equal(7);
        expect(price(13)).to.equal(13);
    });

    it('still charges $1 for the recharged discount plant, whichever copy it is', () => {
        expect(price(6.1, { discount: true, cheapest: 6.1 })).to.equal(1);
        expect(price(6.1, { variant: 'original', discount: true, cheapest: 6.1 })).to.equal(6);
    });

    it('is $0 with no plant chosen', () => {
        expect(options.methods.soleBuyerPrice.call({ soleBuyerPlant: null })).to.equal(0);
    });
});
