import { expect } from 'chai';
import { setup } from './engine';
import { map as hawaii, Regions } from './maps/hawaii';

// The islands in chain order. Region sets must always be a run of neighbours along
// this chain: the Kauai-Big Island ferry never counts as a border (ignoreForRegions).
const CHAIN = [Regions.Green, Regions.Yellow, Regions.Red, Regions.Purple, Regions.Blue, Regions.Brown] as string[];
const STANDARD_PAY = [
    10, 22, 33, 44, 54, 64, 73, 82, 90, 98, 105, 112, 118, 124, 129, 134, 138, 142, 145, 148, 150, 150,
];

describe('HawaiiCustom', () => {
    it('is never dealt by Random', () => {
        for (let s = 0; s < 300; s++) {
            for (const variant of ['original', 'recharged'] as const) {
                expect(setup(3, { map: 'Random', variant }, 'r' + s).map.name).to.not.equal('HawaiiCustom');
            }
        }
    });

    for (let players = 2; players <= 6; players++) {
        it(`deals ${players} players a run of neighbouring islands, never one held only by the ferry`, () => {
            const seen = new Set<string>();
            for (let s = 0; s < 400; s++) {
                const G = setup(players, { map: 'HawaiiCustom', variant: 'original' }, 'h' + s);
                const idx = [...new Set(G.map.cities.map((c) => c.region))]
                    .map((r) => CHAIN.indexOf(r))
                    .sort((a, b) => a - b);
                expect(idx[idx.length - 1] - idx[0], `seed h${s}: ${idx}`).to.equal(idx.length - 1);
                seen.add(idx.join(','));

                const names = new Set(G.map.cities.map((c) => c.name));
                const ferry = G.map.connections.some((c) => c.nodes.includes('Poipu') && c.nodes.includes('Kona'));
                expect(ferry).to.equal(names.has('Poipu') && names.has('Kona'));
            }
            // Every contiguous run of the right length should turn up.
            const want = players <= 3 ? 3 : players === 4 ? 4 : 5;
            expect(seen.size).to.equal(CHAIN.length - want + 1);
        });
    }

    it('pays one Elektro more than the standard table at every step', () => {
        const G = setup(4, { map: 'HawaiiCustom', variant: 'original' }, 'pay');
        expect(G.paymentTable).to.deep.equal(STANDARD_PAY.map((v) => v + 1));
        // Every other map keeps the standard table.
        expect(setup(4, { map: 'Germany', variant: 'original' }, 'pay').paymentTable).to.deep.equal(STANDARD_PAY);
    });

    it('prices houses by island', () => {
        const price = (region: string) => hawaii.cities.find((c) => c.region === region)!.slotCosts;
        expect(price(Regions.Purple)).to.deep.equal([12, 18, 24]);
        expect(price(Regions.Red)).to.deep.equal([11, 17, 22]);
        expect(price(Regions.Yellow)).to.deep.equal([11, 17, 22]);
        for (const r of [Regions.Green, Regions.Blue, Regions.Brown]) expect(price(r)).to.deep.equal([8, 13, 18]);
    });

    it('gives every city at least two links on the full board', () => {
        for (const city of hawaii.cities) {
            const links = hawaii.connections.filter((c) => c.nodes.includes(city.name)).length;
            expect(links, city.name).to.be.at.least(2);
        }
    });
});
