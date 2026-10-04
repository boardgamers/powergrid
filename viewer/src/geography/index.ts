import type { GameMap } from 'powergrid-engine/src/maps';

export type GeographyStyle = 'terrain' | 'wash' | 'line' | 'none';
export type MapBounds = { x: number; y: number; width: number; height: number };
export type MapGeography = { name: string; land: string[]; context: string[]; cities: [string, number, number][] };

const catalog: Record<string, MapGeography> = require('./maps.json');
const byName = Object.fromEntries(Object.values(catalog).map((map) => [map.name, map]));

/** Authored maps and region subsets share coordinates; randomized maps do not. */
export function geographyForMap(map?: GameMap): MapGeography | undefined {
    if (!map?.cities.length) return;
    const geography = byName[map.name];
    if (!geography) return;
    const [rx, ry] = map.adjustRatio || [1, 1];
    if (!map.cities.every((city) => geography.cities.some(([name, x, y]) =>
        name === city.name && Math.abs(city.x - x * rx) < 0.01 && Math.abs(city.y - y * ry) < 0.01
    ))) return;
    return geography;
}
