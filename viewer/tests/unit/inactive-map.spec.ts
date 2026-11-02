import { expect } from 'chai';
import { setup } from 'powergrid-engine';
import { maps, mapsRecharged } from 'powergrid-engine/src/maps';
import { inactiveMapNetwork } from '../../src/util/inactive-map';

describe('unselected map regions', () => {
    it('restores only missing authored spaces, without changing playable cities or legal moves', () => {
        for (const variant of ['original', 'recharged'] as const) {
            for (const authored of variant === 'original' ? maps : mapsRecharged) {
                for (const count of [2, 3, 4, 5, 6]) {
                    const state = setup(count, { map: authored.name as any, variant }, 'context-regions');
                    const before = JSON.stringify(state);
                    const extra = inactiveMapNetwork(state.map, variant);
                    const active = new Set(state.map.cities.map((c) => c.name));
                    const [rx, ry] = state.map.adjustRatio || [1, 1];
                    expect(extra.cities.length + active.size, `${authored.name}/${variant}/${count}`).to.equal(
                        authored.cities.length
                    );
                    for (const city of extra.cities) {
                        const original = authored.cities.find((c) => c.name === city.name)!;
                        expect(active.has(city.name)).to.equal(false);
                        expect([city.x, city.y]).to.deep.equal([original.x * rx, original.y * ry]);
                    }
                    for (const link of extra.links) {
                        expect(link.from).not.to.equal(undefined);
                        expect(link.to).not.to.equal(undefined);
                        expect(active.has(link.from.name) && active.has(link.to.name)).to.equal(false);
                    }
                    expect(JSON.stringify(state)).to.equal(before);
                }
            }
        }
    });
    it('does not invent regions on unknown, empty or randomized maps', () => {
        const map = setup(3, { map: 'Germany', variant: 'original' }, 'context-regions').map;
        for (const input of [
            undefined,
            { ...map, name: 'Unknown' },
            { ...map, cities: [] },
            { ...map, cities: map.cities.map((c, i) => ({ ...c, x: c.x + (i ? 0 : 5) })) },
        ]) {
            expect(inactiveMapNetwork(input, 'original')).to.deep.equal({ cities: [], links: [] });
        }
    });
});
