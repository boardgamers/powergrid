import type { GameState } from 'powergrid-engine';

/**
 * The row model behind the portrait resource market (`boards/ResourceBoxes.vue`).
 *
 * Kept out of the component so it can be tested against the engine directly: every
 * row's `price` is the money the engine will actually take for the next cube bought
 * from that source, and `resource-rows.spec.ts` asserts exactly that by buying one.
 *
 * Written without optional chaining: webpack 4 parses the unit-test bundle and
 * rejects `?.` (same note as `util/turn-buffer.ts`).
 */

export type BuyMove = { resource: string; side?: 'north' | 'south'; fromStorage?: boolean };

export interface ResourceRow {
    label: string;
    color: string;
    /** What a tap sends. Identical in shape to the engine's BuyResource payload. */
    move: BuyMove;
    /** What the engine charges for the next cube here, or null when it is empty. */
    price: number | null;
    /** The price once the cubes at the current price run out. */
    next: number | null;
    /** How many cubes are still on sale at `price`. Zero for a flat pool. */
    atPrice: number;
    /** Cubes left in this source altogether. */
    cubes: number;
    buyable: boolean;
    /** On the board but above the per-step price cap, so nobody may buy it yet. */
    capped: boolean;
    /** A flat-price pool with no track behind it: every cube costs the same. */
    flat: boolean;
    title: string;
}

export interface ResourceBlock {
    title?: string;
    restock?: string;
    rows: ResourceRow[];
}

export const RESOURCE_COLORS: Record<string, string> = {
    coal: '#6b2028',
    oil: '#15130f',
    garbage: '#f2d024',
    uranium: '#dc2626',
};

/** The engine's own defaults, for maps that do not author their own arrays. */
const DEFAULT_PRICES: Record<string, number[]> = {
    coal: [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8],
    oil: [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8],
    garbage: [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8],
    uranium: [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16],
};

const FLAT_POOL_PRICE = 8;

export interface RowOptions {
    /** The seat reading the board — only needed for Central Europe's Wien discount. */
    player?: number;
    buyable?: BuyMove[];
    /** Resupply for this step, indexed coal / oil / garbage / uranium. */
    resupply?: (number | string)[];
    resupplyNorth?: (number | string)[];
    isUsaRecharged?: boolean;
}

function capitalize(s: string): string {
    return s[0].toUpperCase() + s.slice(1);
}

function isKorea(G: GameState): boolean {
    return G.coalPricesNorth !== undefined;
}

/** India and friends only sell up to a per-step price. 16 = no cap in practice. */
function maxPrice(G: GameState): number {
    const table = (G.map as { maxPriceAvailable?: number[] }).maxPriceAvailable;
    return table ? table[G.step - 1] : 16;
}

function pricesFor(G: GameState, resource: string, north: boolean): number[] {
    const bag = G as unknown as Record<string, number[] | undefined>;
    const authored = bag[resource + 'Prices' + (north ? 'North' : '')];
    return authored !== undefined ? authored : DEFAULT_PRICES[resource];
}

function cubesIn(G: GameState, resource: string, north: boolean): number {
    const bag = G as unknown as Record<string, number | undefined>;
    const count = bag[resource + 'Market' + (north ? 'North' : '')];
    return count === undefined ? 0 : count;
}

function sameMove(a: BuyMove, b: BuyMove): boolean {
    return a.resource === b.resource && a.side === b.side && !!a.fromStorage === !!b.fromStorage;
}

/**
 * Central Europe sells garbage a dollar cheaper to whoever holds Wien — and the
 * engine really does charge the lower price, not just offer the move. The box shows
 * the price THIS player would pay, because that is the only number a tap can act on.
 */
function wienDiscount(G: GameState, resource: string, player: number | undefined): number {
    if (resource !== 'garbage' || G.map.name !== 'Central Europe' || player === undefined) return 0;
    const me = G.players[player];
    if (!me) return 0;
    return me.cities.some((c) => c.name === 'Wien') ? 1 : 0;
}

function marketRow(G: GameState, resource: string, north: boolean, opts: RowOptions): ResourceRow {
    const prices = pricesFor(G, resource, north);
    const cubes = cubesIn(G, resource, north);
    // Cubes fill from the dear end, so the next one sold is at `length - cubes`.
    // Clamped only so a market holding more cubes than its track has slots reads as
    // the cheapest price rather than as a blank — the engine indexes the same array
    // the same way, so it could not price such a state either. Middle East's "surplus
    // oil" is not that case: its track is the full 24 and the surplus IS the $1 end.
    const idx = Math.max(0, prices.length - cubes);

    let price: number | null = null;
    let atPrice = 0;
    let next: number | null = null;

    if (cubes > 0) {
        price = prices[idx] - (north ? 0 : wienDiscount(G, resource, opts.player));
        for (let i = idx; i < prices.length && prices[i] === prices[idx]; i++) atPrice++;
        for (let i = idx; i < prices.length; i++) {
            if (prices[i] !== prices[idx]) {
                next = prices[i] - (north ? 0 : wienDiscount(G, resource, opts.player));
                break;
            }
        }
    }

    const move: BuyMove = isKorea(G) ? { resource, side: north ? 'north' : 'south' } : { resource };

    return {
        label: capitalize(resource),
        color: RESOURCE_COLORS[resource],
        move,
        price,
        next,
        atPrice,
        cubes,
        buyable: !!opts.buyable && opts.buyable.some((b) => sameMove(b, move)),
        capped: price !== null && price > maxPrice(G),
        flat: false,
        title:
            cubes > 0
                ? `${capitalize(resource)} — $${price} each, ${atPrice} at that price, ${cubes} left`
                : `${capitalize(resource)} — market empty`,
    };
}

/** South Africa's storage pool and USA recharged's supply: a flat $8, no track. */
function flatRow(G: GameState, cubes: number, fromStorage: boolean, label: string, opts: RowOptions): ResourceRow {
    const move: BuyMove = fromStorage ? { resource: 'coal', fromStorage: true } : { resource: 'coal' };
    return {
        label,
        color: RESOURCE_COLORS.coal,
        move,
        price: cubes > 0 ? FLAT_POOL_PRICE : null,
        next: null,
        atPrice: 0,
        cubes,
        buyable: !!opts.buyable && opts.buyable.some((b) => sameMove(b, move)),
        capped: cubes > 0 && FLAT_POOL_PRICE > maxPrice(G),
        flat: true,
        title: `${label} — $${FLAT_POOL_PRICE} each, ${cubes} left`,
    };
}

/**
 * Does this map sell uranium on the main track at all? Australia moves it to a
 * separate mine market and Bremen has no nuclear, so on both the row would be a
 * permanently empty box.
 */
function uraniumOnTrack(G: GameState): boolean {
    return G.map.name !== 'Australia' && G.map.name !== 'Bremen';
}

function rowsFor(G: GameState, north: boolean, opts: RowOptions): ResourceRow[] {
    const rows: ResourceRow[] = [];

    // USA recharged keeps selling coal at a flat $8 out of the supply once the printed
    // track is bare, so the row would otherwise read "out" while the move is on offer.
    if (!north && opts.isUsaRecharged && G.coalMarket === 0 && G.coalSupply > 0) {
        rows.push(flatRow(G, G.coalSupply, false, 'Coal (from supply)', opts));
    } else {
        rows.push(marketRow(G, 'coal', north, opts));
    }

    // South Africa: used coal returns to a storage pool below the market and can
    // always be bought back at $8, alongside whatever the track is charging. It sits
    // directly under the market coal rather than at the bottom of the list, so the two
    // coal prices are read together — the track is usually the cheaper of the two and
    // that should be obvious without hunting.
    if (!north && G.coalStorage !== undefined) {
        rows.push(flatRow(G, G.coalStorage, true, 'Coal (from storage)', opts));
    }

    rows.push(marketRow(G, 'oil', north, opts));
    rows.push(marketRow(G, 'garbage', north, opts));

    // Korea's north side has no uranium row.
    if (!north && uraniumOnTrack(G)) {
        rows.push(marketRow(G, 'uranium', north, opts));
    }

    return rows;
}

/**
 * The resupply table is indexed coal / oil / garbage / uranium, and the track rows
 * are drawn in that order — so the numbers line up with the boxes below them. Rows
 * that are not part of the printed track (the flat pools) get no number.
 */
function restockText(table: (number | string)[] | undefined, rows: ResourceRow[]): string | undefined {
    if (!table) return undefined;
    const numbers = rows.filter((r) => !r.flat).map((r, i) => table[i]);
    return numbers.every((n) => n === undefined) ? undefined : numbers.filter((n) => n !== undefined).join(' / ');
}

export function resourceBlocks(G: GameState, opts: RowOptions = {}): ResourceBlock[] {
    const blocks: ResourceBlock[] = [];

    if (isKorea(G)) {
        const northRows = rowsFor(G, true, opts);
        blocks.push({
            title: 'North Market',
            restock: restockText(opts.resupplyNorth, northRows),
            rows: northRows,
        });
    }

    const southRows = rowsFor(G, false, opts);
    blocks.push({
        title: isKorea(G) ? 'South Market' : undefined,
        restock: restockText(opts.resupply, southRows),
        rows: southRows,
    });

    return blocks;
}
