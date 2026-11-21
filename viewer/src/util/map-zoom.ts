// Zoom for the map slot only. The board is one SVG laid out to fit the screen; this
// adds a second, player-controlled zoom on top of that fit, around the map alone.
//
// Everything is in scene units (the SVG's viewBox space). A zoom is a uniform scale
// `k` plus a translation, applied as `translate(x, y) scale(k)` to a group whose
// untransformed contents fill `rect`, the map's laid-out box. The map never zooms
// out past the fitted size, and is clamped so it always covers its own box: you
// cannot pan the board off into empty space.

export interface MapZoom {
    k: number;
    x: number;
    y: number;
}

export interface Rect {
    x: number;
    y: number;
    width: number;
    height: number;
}

export const MAP_ZOOM_MIN = 1;
export const MAP_ZOOM_MAX = 4;
/** One button press or wheel notch. */
export const MAP_ZOOM_STEP = 1.25;

export const IDENTITY: MapZoom = { k: 1, x: 0, y: 0 };

export function isZoomed(z: MapZoom): boolean {
    return z.k > MAP_ZOOM_MIN + 1e-6;
}

/** Keep the scaled map covering `rect`: no gap may open on any side. */
export function clampZoom(z: MapZoom, rect: Rect): MapZoom {
    const k = Math.min(MAP_ZOOM_MAX, Math.max(MAP_ZOOM_MIN, z.k));
    if (k <= MAP_ZOOM_MIN + 1e-6) return { ...IDENTITY };
    // A point p maps to k * p + t. The left edge must not move right of rect.x,
    // and the right edge must not move left of rect.x + rect.width.
    const right = rect.x + rect.width;
    const bottom = rect.y + rect.height;
    const x = Math.min(rect.x * (1 - k), Math.max(right * (1 - k), z.x));
    const y = Math.min(rect.y * (1 - k), Math.max(bottom * (1 - k), z.y));
    return { k, x, y };
}

/**
 * Scale by `factor` about the scene point (px, py), so the point under the cursor or
 * between the fingers stays where it is.
 */
export function zoomAt(z: MapZoom, factor: number, px: number, py: number, rect: Rect): MapZoom {
    const k = Math.min(MAP_ZOOM_MAX, Math.max(MAP_ZOOM_MIN, z.k * factor));
    const applied = k / z.k;
    return clampZoom({ k, x: px - (px - z.x) * applied, y: py - (py - z.y) * applied }, rect);
}

/** Zoom about the centre of the map's box (the + and − buttons). */
export function zoomCentre(z: MapZoom, factor: number, rect: Rect): MapZoom {
    return zoomAt(z, factor, rect.x + rect.width / 2, rect.y + rect.height / 2, rect);
}

/** Move by (dx, dy) scene units. */
export function pan(z: MapZoom, dx: number, dy: number, rect: Rect): MapZoom {
    return clampZoom({ k: z.k, x: z.x + dx, y: z.y + dy }, rect);
}

export function zoomTransform(z: MapZoom): string | undefined {
    if (!isZoomed(z)) return undefined;
    const r = (n: number) => Math.round(n * 100) / 100;
    return `translate(${r(z.x)}, ${r(z.y)}) scale(${Math.round(z.k * 10000) / 10000})`;
}

/** The part of the fitted map (in unzoomed scene units) that is on screen. */
export function visibleRect(z: MapZoom, rect: Rect): Rect {
    return {
        x: (rect.x - z.x) / z.k,
        y: (rect.y - z.y) / z.k,
        width: rect.width / z.k,
        height: rect.height / z.k,
    };
}

/** Keep the zoom level, and bring the unzoomed scene point (px, py) to the middle of the view. */
export function centreOn(z: MapZoom, px: number, py: number, rect: Rect): MapZoom {
    return clampZoom({ k: z.k, x: rect.x + rect.width / 2 - z.k * px, y: rect.y + rect.height / 2 - z.k * py }, rect);
}

/** Minimap size on screen, in CSS px: big enough to read, never a second map. */
export const MINIMAP_MIN_PX = 72;
export const MINIMAP_MAX_PX = 128;
export const MINIMAP_SHARE = 0.195;
export const MINIMAP_MARGIN_PX = 8;

export interface Minimap extends Rect {
    /** Maps the map's box onto the minimap's box. */
    scale: number;
}

/**
 * The minimap's box in scene units, in the bottom-left corner of the map's box (the
 * zoom buttons sit top-right). Its longer side is about a quarter of the map's on
 * screen, clamped between MINIMAP_MIN_PX and MINIMAP_MAX_PX.
 */
export function minimapBox(rect: Rect, pxPerUnit: number): Minimap {
    const longSide = Math.max(rect.width, rect.height);
    const longPx = Math.min(MINIMAP_MAX_PX, Math.max(MINIMAP_MIN_PX, longSide * pxPerUnit * MINIMAP_SHARE));
    const scale = longPx / pxPerUnit / longSide;
    const width = rect.width * scale;
    const height = rect.height * scale;
    const margin = MINIMAP_MARGIN_PX / pxPerUnit;
    return { x: rect.x + margin, y: rect.y + rect.height - margin - height, width, height, scale };
}

/** How far a press may travel and still count as a click rather than a pan, in CSS px. */
export const CLICK_SLOP_PX = 6;
