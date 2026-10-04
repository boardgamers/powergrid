import { expect } from 'chai';
import { setup } from 'powergrid-engine';
import { maps, mapsRecharged, GameMap } from 'powergrid-engine/src/maps';
import { geographyForMap } from '../../src/geography';

const catalog = require('../../src/geography/maps.json');

describe('geographic backgrounds', () => {
    it('covers every authored map in both editions without changing its data', () => {
        expect(Object.keys(catalog)).to.have.length(maps.length);
        for (const authored of [...maps, ...mapsRecharged]) {
            const [rx, ry] = authored.adjustRatio || [1, 1];
            const map = { ...authored, cities: authored.cities.map(c => ({ ...c, x: c.x * rx, y: c.y * ry })) };
            const before = JSON.stringify(map);
            const geography = geographyForMap(map);
            expect(geography, authored.name).not.to.equal(undefined);
            expect(geography!.land.length, authored.name).to.be.greaterThan(0);
            expect(geography!.context.length, authored.name).to.be.greaterThan(0);
            expect(JSON.stringify(map)).to.equal(before);
        }
    });
    it('recognizes real region subsets for both editions and different player counts', () => {
        for (const variant of ['original', 'recharged'] as const) {
            for (const authored of (variant === 'original' ? maps : mapsRecharged)) {
                for (const count of [3, 4]) {
                    const state = setup(count, { map: authored.name as any, variant }, 'geography');
                    expect(geographyForMap(state.map), `${authored.name}/${variant}/${count}`).not.to.equal(undefined);
                }
            }
        }
    });
    it('leaves unknown, empty and randomized layouts without geographic decoration', () => {
        const map = setup(3, { map: 'Germany', variant: 'original' }, 'geography').map;
        expect(geographyForMap()).to.equal(undefined);
        expect(geographyForMap({ ...map, name: 'Unknown' })).to.equal(undefined);
        expect(geographyForMap({ ...map, cities: [] })).to.equal(undefined);
        const random: GameMap = { ...map, cities: map.cities.map((c, i) => ({ ...c, x: c.x + (i ? 0 : 10) })) };
        expect(geographyForMap(random)).to.equal(undefined);
    });
});
