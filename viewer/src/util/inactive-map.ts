import type { City, GameMap } from 'powergrid-engine/src/maps';
import { maps, mapsRecharged } from 'powergrid-engine/src/maps';

export interface InactiveMapNetwork {
    cities: City[];
    links: { from: City; to: City }[];
}

/** Decorative only: never add these spaces or links to the playable game state. */
export function inactiveMapNetwork(map?: GameMap, variant?: string): InactiveMapNetwork {
    const empty = { cities: [], links: [] };
    if (!map?.cities.length) return empty;
    const authored = (variant === 'original' ? maps : mapsRecharged).find((m) => m.name === map.name);
    if (!authored) return empty;
    const [rx, ry] = map.adjustRatio || [1, 1];
    const cities = authored.cities.map((c) => ({ ...c, x: c.x * rx, y: c.y * ry }));
    const byName = new Map(cities.map((c) => [c.name, c]));
    // Randomized layouts retain a map name but no longer share its coordinates.
    if (
        !map.cities.every((c) => {
            const original = byName.get(c.name);
            return original && Math.abs(c.x - original.x) < 0.01 && Math.abs(c.y - original.y) < 0.01;
        })
    )
        return empty;
    const active = new Set(map.cities.map((c) => c.name));
    return {
        cities: cities.filter((c) => !active.has(c.name)),
        links: authored.connections
            .filter((c) => c.nodes.some((name) => !active.has(name)))
            .map((c) => ({ from: byName.get(c.nodes[0])!, to: byName.get(c.nodes[1])! })),
    };
}
