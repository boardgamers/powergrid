import seedrandom from 'seedrandom';

/* eslint-disable */
export function asserts<T>(move: any): asserts move is T {}

/* eslint-enable */

/**
 * Return the element of `array` with the smallest `key(element)`. Ties go to
 * the earlier element. Returns `undefined` if the array is empty.
 */
export function minBy<T>(array: readonly T[], key: (item: T) => number): T | undefined {
    let best: T | undefined;
    let bestKey = Infinity;
    for (const item of array) {
        const k = key(item);
        if (k < bestKey) {
            best = item;
            bestKey = k;
        }
    }
    return best;
}

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
