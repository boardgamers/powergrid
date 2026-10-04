import type { GameMap } from 'powergrid-engine/src/maps';
import { geographyLoaders } from './loaders';

export type GeographyStyle = 'terrain' | 'wash' | 'line' | 'none';
export type MapBounds = { x: number; y: number; width: number; height: number };
export type MapGeography = { name: string; land: string[]; context: string[]; cities: [string, number, number][] };

let byName: Record<string, MapGeography> = {};
const keys: Record<string, string> = require('./names.json');
const pending: Record<string, Promise<void> | undefined> = {};

/** Fetch only the current map; the larger off-board area stays out of the entry. */
export function loadGeography(name: string): Promise<void> {
    const key = keys[name] as keyof typeof geographyLoaders;
    if (!key) return Promise.resolve();
    if (!pending[key]) {
        pending[key] = geographyLoaders[key]()
            .then((module) => {
                byName[name] = module.default as unknown as MapGeography;
            })
            .catch((error) => {
                delete pending[key];
                throw error;
            });
    }
    return pending[key]!;
}

/** Used by asset validation; the game loads one named map at a time. */
export async function loadGeographies(): Promise<void> {
    await Promise.all(Object.keys(keys).map(loadGeography));
}

/** Authored maps and region subsets share coordinates; randomized maps do not. */
export function geographyForMap(map?: GameMap): MapGeography | undefined {
    if (!map?.cities.length) return;
    const geography = byName[map.name];
    if (!geography) return;
    const [rx, ry] = map.adjustRatio || [1, 1];
    if (
        !map.cities.every((city) =>
            geography.cities.some(
                ([name, x, y]) =>
                    name === city.name && Math.abs(city.x - x * rx) < 0.01 && Math.abs(city.y - y * ry) < 0.01
            )
        )
    )
        return;
    return geography;
}
