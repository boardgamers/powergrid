import Delaunator from 'delaunator';
import { upperFirst } from 'lodash';
import seedrandom from 'seedrandom';
import { City, Connection, GameMap } from './maps';

const widthByRegions = [420, 490, 490];
const heightByRegions = [490, 560, 700];

export function createRandomizedMap(map: GameMap, regionCount: number, rng: seedrandom.prng) {
    const regions = [...new Set(map.cities.map((c) => c.region))];
    const cities = Array(7 * regionCount)
        .fill(0)
        .map((_) => ({ name: '', region: '', x: 0, y: 0 }));
    const width = widthByRegions[regionCount - 3];
    const height = heightByRegions[regionCount - 3];
    const gridCellSize = 70;
    const gridWidth = Math.ceil(width / gridCellSize);
    const gridHeight = Math.ceil(height / gridCellSize);
    const gridLength = gridWidth * gridHeight;
    const grid = Array(gridLength).fill(-1);

    map.mapPosition = [100, 200];
    map.layout = 'Portrait';

    let emptyGrids = Array(gridLength)
        .fill(0)
        .map((_, i) => i);
    cities.forEach((city, i) => {
        const emptyGrid = emptyGrids[Math.floor(rng() * emptyGrids.length)];
        const emptyGridY = Math.floor(emptyGrid / gridWidth);
        const emptyGridX = emptyGrid % gridWidth;
        city.x = Math.floor(emptyGridX * 2 * gridCellSize);
        city.y = Math.floor(emptyGridY * gridCellSize);
        if (emptyGridY % 2 === 0) {
            city.x += gridCellSize;
        }

        var t = rng() * 2 * Math.PI;
        var r = (rng() * gridCellSize) / 2;
        city.x += r * Math.cos(t);
        city.y += r * Math.sin(t);

        emptyGrids = emptyGrids.filter((g) => g !== emptyGrid);
        grid[emptyGrid] = i;
    });

    const cityDists: number[][] = Array(cities.length)
        .fill(0)
        .map((_) => Array(cities.length).fill(0));
    const cityConnections: boolean[][] = Array(cities.length)
        .fill(0)
        .map((_) => Array(cities.length).fill(null));
    const d = Delaunator.from(
        cities,
        (c: City) => c.x,
        (c: City) => c.y
    );
    for (let i = 0; i < d.triangles.length; i += 3) {
        const city1 = cities[d.triangles[i]];
        const city2 = cities[d.triangles[i + 1]];
        const city3 = cities[d.triangles[i + 2]];

        let dist = cityDists[d.triangles[i]][d.triangles[i + 1]];
        const dist12Squared = dist
            ? Math.pow(dist, 2)
            : Math.pow(city1.x - city2.x, 2) + Math.pow(city1.y - city2.y, 2);
        const dist12 =
            dist ||
            (cityDists[d.triangles[i + 1]][d.triangles[i]] = cityDists[d.triangles[i]][d.triangles[i + 1]] =
                Math.sqrt(dist12Squared));

        dist = cityDists[d.triangles[i]][d.triangles[i + 2]];
        const dist13Squared = dist
            ? Math.pow(dist, 2)
            : Math.pow(city1.x - city3.x, 2) + Math.pow(city1.y - city3.y, 2);
        const dist13 =
            dist ||
            (cityDists[d.triangles[i + 2]][d.triangles[i]] = cityDists[d.triangles[i]][d.triangles[i + 2]] =
                Math.sqrt(dist13Squared));

        dist = cityDists[d.triangles[i + 1]][d.triangles[i + 2]];
        const dist23Squared = dist
            ? Math.pow(dist, 2)
            : Math.pow(city2.x - city3.x, 2) + Math.pow(city2.y - city3.y, 2);
        const dist23 =
            dist ||
            (cityDists[d.triangles[i + 2]][d.triangles[i + 1]] = cityDists[d.triangles[i + 1]][d.triangles[i + 2]] =
                Math.sqrt(dist23Squared));

        // arccos((P122 + P132 - P232) / (2 * P12 * P13))
        const angle1 = Math.acos((dist12Squared + dist13Squared - dist23Squared) / (2 * dist12 * dist13));
        const angle2 = Math.acos((dist12Squared + dist23Squared - dist13Squared) / (2 * dist12 * dist23));
        const angle3 = Math.PI - angle1 - angle2;

        const maxAngle = (105 * Math.PI) / 180;
        if (cityConnections[d.triangles[i]][d.triangles[i + 1]] !== false && angle3 < maxAngle) {
            cityConnections[d.triangles[i]][d.triangles[i + 1]] = true;
            cityConnections[d.triangles[i + 1]][d.triangles[i]] = true;
        } else {
            cityConnections[d.triangles[i]][d.triangles[i + 1]] = false;
            cityConnections[d.triangles[i + 1]][d.triangles[i]] = false;
        }

        if (cityConnections[d.triangles[i]][d.triangles[i + 2]] !== false && angle2 < maxAngle) {
            cityConnections[d.triangles[i]][d.triangles[i + 2]] = true;
            cityConnections[d.triangles[i + 2]][d.triangles[i]] = true;
        } else {
            cityConnections[d.triangles[i]][d.triangles[i + 2]] = false;
            cityConnections[d.triangles[i + 2]][d.triangles[i]] = false;
        }

        if (cityConnections[d.triangles[i + 1]][d.triangles[i + 2]] !== false && angle1 < maxAngle) {
            cityConnections[d.triangles[i + 1]][d.triangles[i + 2]] = true;
            cityConnections[d.triangles[i + 2]][d.triangles[i + 1]] = true;
        } else {
            cityConnections[d.triangles[i + 1]][d.triangles[i + 2]] = false;
            cityConnections[d.triangles[i + 2]][d.triangles[i + 1]] = false;
        }
    }

    let maxDist = 0;
    let minDist = 1000;
    for (let i = 0; i < cities.length; i++) {
        for (let j = 0; j < i; j++) {
            if (cityConnections[i][j]) {
                const dist = cityDists[i][j];
                maxDist = Math.max(maxDist, dist);
                minDist = Math.min(minDist, dist);
            }
        }
    }

    const centroids =
        regionCount === 5
            ? [
                  [width / 4, height / 4],
                  [width / 4, (3 * height) / 4],
                  [width / 2, height / 2],
                  [(3 * width) / 4, height / 4],
                  [(3 * width) / 4, (3 * height) / 4],
              ]
            : regionCount === 4
            ? [
                  [width / 4, height / 4],
                  [width / 4, (3 * height) / 4],
                  [(3 * width) / 4, height / 4],
                  [(3 * width) / 4, (3 * height) / 4],
              ]
            : [
                  [width / 4, height / 4],
                  [width / 2, height / 2],
                  [(3 * width) / 4, (3 * height) / 4],
              ];
    const indexes = bkmeans(
        cities.map((c) => [c.x, c.y]),
        regionCount,
        centroids,
        cityConnections
    );
    const countRegions = Array(regionCount).fill(0);
    cities.forEach((city, index) => {
        city.region = regions[indexes[index]];
        city.name = upperFirst(city.region) + ' ' + (countRegions[indexes[index]]++ + 1);
    });

    const connections: Connection[] = [];
    for (let i = 0; i < cities.length; i++) {
        for (let j = 0; j < i; j++) {
            if (cityConnections[i][j]) {
                const city1 = cities[i];
                const city2 = cities[j];
                const dist = cityDists[i][j];
                connections.push({
                    nodes: [city1.name, city2.name],
                    cost: Math.floor((5 * dist) / gridCellSize),
                });
            }
        }
    }

    map.cities = cities;
    map.connections = connections;

    return map;
}

function bkmeans(
    points: number[][],
    regions: number,
    centroids: number[][],
    connections: boolean[][],
    iterations: number = 100
): number[] {
    const indexes = Array(points.length).fill(0);
    const pointsPerRegion = Math.ceil(points.length / regions);

    let conv = false;
    do {
        // Assign
        const regionsCount = Array(regions).fill(0);
        const pointCentDists = Array(points.length)
            .fill(0)
            .map((_) => Array(regions).fill(0));
        points.forEach((point, pi) => {
            let minDist: number | null = null;
            let index = 0;
            centroids.forEach((centroid, ci) => {
                const d = dist(point, centroid);
                if (minDist === null || d < minDist) {
                    if (regionsCount[ci] < pointsPerRegion) {
                        minDist = d;
                        index = ci;
                    }
                }

                pointCentDists[pi][ci] = d;
            });

            indexes[pi] = index;
            regionsCount[index]++;
        });

        // Update
        const newCentroids = Array(centroids.length)
            .fill(0)
            .map((_) => [0, 0]);
        const centroidsCount = Array(centroids.length).fill(0);
        points.forEach((point, pi) => {
            newCentroids[indexes[pi]][0] += point[0];
            newCentroids[indexes[pi]][1] += point[1];
            centroidsCount[indexes[pi]]++;
        });

        conv = true;
        centroids.forEach((centroid, ci) => {
            newCentroids[ci][0] = newCentroids[ci][0] / centroidsCount[ci];
            newCentroids[ci][1] = newCentroids[ci][1] / centroidsCount[ci];

            if (centroid[0] !== newCentroids[ci][0] || centroid[1] !== newCentroids[ci][1]) {
                conv = false;
            }
        });

        centroids = newCentroids;

        console.log('iterations', iterations);
        console.log('centroids', centroids);

        conv = conv || --iterations === 0;
    } while (!conv);

    // Refine
    let maxRefine = 10;
    do {
        console.log('Refining');
        conv = true;
        points.forEach((_, p1) => {
            const index = indexes[p1];
            const hasSameColorNeighbor = connections[p1].some((connection, p2) => connection && index === indexes[p2]);
            if (!hasSameColorNeighbor) {
                const centroid = centroids[index];
                let minDist: number | null = null;
                let closestNeighbor: number | null = null;
                connections[p1].forEach((connection, p2) => {
                    if (connection) {
                        const neighbor = points[p2];
                        const d = dist(neighbor, centroid);
                        if (minDist === null || d < minDist) {
                            minDist = d;
                            closestNeighbor = p2;
                        }
                    }
                });

                indexes[p1] = indexes[closestNeighbor!];
                indexes[closestNeighbor!] = index;

                conv = false;
            }
        });
        conv = conv || --maxRefine === 0;
    } while (!conv);

    return indexes;
}

function dist(p1: number[], p2: number[]): number {
    return (p1[0] - p2[0]) * (p1[0] - p2[0]) + (p1[1] - p2[1]) * (p1[1] - p2[1]);
}
