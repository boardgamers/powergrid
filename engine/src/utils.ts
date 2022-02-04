import seedrandom from 'seedrandom';

/* eslint-disable */
export function asserts<T>(move: any): asserts move is T {}

/* eslint-enable */

export function shuffle<T>(array: T[], seed: string): T[] {
    const rng = seedrandom.alea(seed);
    const reverse = new Map<number, number>();

    array.forEach((item, i) => {
        let n = rng.int32();

        while (reverse.has(n)) {
            n = rng.int32();
        }

        reverse.set(n, i);
    });

    return [...reverse.keys()].sort().map((n) => array[reverse.get(n)!]);
}
