export interface BoardBox {
    x: number;
    y: number;
    width: number;
    height: number;
    /** Occupied areas in the same coordinates as the box; omitted means solid. */
    parts?: BoardBox[];
}

export interface BoardPlacement extends BoardBox {
    scale: number;
    transform: string;
}

const PAD = 16;
const GAP = 20;
// The network needs stroke clearance, not the wider spacing between UI panels.
const MAP_GAP = 8;
const rounded = (n: number) => Number(n.toFixed(4));

/** Prioritise readable cities on wide, short screens, while keeping the UI's
 * smallest text at least as large as it is on a typical laptop display. */
export function desktopBoardLayout(
    boxes: Record<string, BoardBox>,
    width: number,
    targetHeight: number,
    display?: { pixelsPerUnit: number; cityDiameter: number }
) {
    const normal = packDesktopBoard(boxes, width, targetHeight, 1);
    if (!display || display.cityDiameter <= 0 || display.pixelsPerUnit <= 0 || !normal.placements.map) return normal;
    const cityPixels = (layout: typeof normal) =>
        layout.placements.map.scale * display.cityDiameter * display.pixelsPerUnit;
    const target = 36;
    if (cityPixels(normal) >= target) return normal;
    // Do not deliberately shrink 15-unit income text below 11.25 CSS pixels
    // (existing row-width limits still apply), or reduce controls by over 35%.
    let low = Math.min(1, Math.max(0.65, 0.75 / display.pixelsPerUnit)),
        high = 1;
    let best = packDesktopBoard(boxes, width, targetHeight, low);
    if (cityPixels(best) < target) {
        // Height is a preference, not a readability limit. Grow the scene when
        // compacting controls cannot produce 36 CSS-pixel cities. Width still
        // limits the map, so very narrow desktops use the largest size that fits.
        let minHeight = targetHeight;
        let maxHeight = targetHeight + Object.values(boxes).reduce((sum, box) => sum + box.height + GAP, 0);
        best = packDesktopBoard(boxes, width, maxHeight, low);
        const attainable = Math.min(target, cityPixels(best));
        for (let i = 0; i < 16; i++) {
            const height = (minHeight + maxHeight) / 2;
            const layout = packDesktopBoard(boxes, width, height, low);
            if (cityPixels(layout) >= attainable) {
                maxHeight = height;
                best = layout;
            } else minHeight = height;
        }
        return best;
    }
    if (cityPixels(best) <= cityPixels(normal) * 1.01) return normal;
    // Use the largest controls that still meet the city-size target.
    for (let i = 0; i < 8; i++) {
        const ceiling = (low + high) / 2;
        const layout = packDesktopBoard(boxes, width, targetHeight, ceiling);
        if (cityPixels(layout) >= target) {
            low = ceiling;
            best = layout;
        } else high = ceiling;
    }
    return best;
}

/** Pack measured game components; decorative geography never participates. */
function packDesktopBoard(boxes: Record<string, BoardBox>, width: number, targetHeight: number, chromeCeiling: number) {
    const placements: Record<string, BoardPlacement> = {};
    const present = (names: string[]) =>
        names.filter((name) => boxes[name] && boxes[name].width > 0 && boxes[name].height > 0);
    const header = present(['cityCount', 'powerPlantDeck', 'powerPlantMarket', 'buttons']);
    const footer = present(['resources', 'roundInfo']);
    const sidebar = present(['playerOrder', 'playerBoards']);
    const usable = width - PAD * 2;
    const rowScale = (names: string[], ceiling: number) =>
        Math.min(
            ceiling,
            (usable - GAP * Math.max(0, names.length - 1)) /
                Math.max(
                    1,
                    names.reduce((n, name) => n + boxes[name].width, 0)
                )
        );
    const rowHeight = (names: string[], scale: number) =>
        Math.max(0, ...names.map((name) => boxes[name].height * scale));
    const fixedHeight = rowHeight(header, rowScale(header, 1)) + rowHeight(footer, rowScale(footer, 1));
    // On short landscape screens, keep some room for the map instead of letting
    // the header and a two-market resource track consume the entire viewport.
    const chrome = Math.min(
        chromeCeiling,
        Math.max(0.6, (targetHeight - 180 - PAD * 2 - GAP * 2) / Math.max(1, fixedHeight))
    );
    const headerScale = rowScale(header, chrome);
    const footerScale = rowScale(footer, chrome);
    const headerHeight = rowHeight(header, headerScale);
    const footerHeight = rowHeight(footer, footerScale);
    const bodyTop = PAD + headerHeight + GAP;
    const bodyBudget = Math.max(180, targetHeight - bodyTop - GAP - footerHeight - PAD);

    function place(name: string, x: number, y: number, scale: number) {
        const box = boxes[name];
        placements[name] = {
            x,
            y,
            width: box.width * scale,
            height: box.height * scale,
            scale,
            transform: `translate(${rounded(x - box.x * scale)}, ${rounded(y - box.y * scale)}) scale(${rounded(
                scale
            )})`,
        };
    }
    function placeRow(names: string[], y: number, scale: number, alignTop = false) {
        const height = rowHeight(names, scale);
        const occupied = names.reduce((n, name) => n + boxes[name].width * scale, 0);
        const gap = names.length > 1 ? (usable - occupied) / (names.length - 1) : 0;
        let x = PAD;
        for (const name of names) {
            place(name, x, y + (alignTop ? 0 : (height - boxes[name].height * scale) / 2), scale);
            x += boxes[name].width * scale + gap;
        }
    }
    placeRow(header, PAD, headerScale, true);

    const sidebarWidth = Math.min(
        usable * (boxes.playerBoards?.width > 600 ? 0.43 : 0.28),
        Math.max(0, ...sidebar.map((name) => boxes[name].width)) * chrome
    );
    const sidebarNaturalHeight = sidebar.reduce((n, name) => n + boxes[name].height, 0);
    const sidebarScale = sidebar.length
        ? Math.min(
              chrome,
              sidebarWidth / Math.max(...sidebar.map((name) => boxes[name].width)),
              (bodyBudget - GAP * (sidebar.length - 1)) / sidebarNaturalHeight
          )
        : 1;
    let sidebarY = bodyTop;
    for (const name of sidebar) {
        place(name, width - PAD - sidebarWidth, sidebarY, sidebarScale);
        sidebarY += boxes[name].height * sidebarScale + GAP;
    }
    const leftWidth = usable - (sidebar.length ? sidebarWidth + GAP : 0);
    let mapX = PAD;
    let mapWidth = leftWidth;
    let bodyHeight = sidebar.length ? sidebarY - GAP - bodyTop : 0;
    if (boxes.uraniumMines) {
        const scale = Math.min(chrome, bodyBudget / boxes.uraniumMines.height);
        place('uraniumMines', PAD, bodyTop, scale);
        mapX += placements.uraniumMines.width + GAP;
        mapWidth -= placements.uraniumMines.width + GAP;
        bodyHeight = Math.max(bodyHeight, placements.uraniumMines.height);
    }
    const freeJumpScale = boxes.freeJump ? Math.min(chrome, mapWidth / boxes.freeJump.width) : 1;
    const freeJumpHeight = boxes.freeJump ? boxes.freeJump.height * freeJumpScale + GAP : 0;
    if (boxes.map) {
        const scale = Math.min(1, mapWidth / boxes.map.width, (bodyBudget - freeJumpHeight) / boxes.map.height);
        place('map', mapX + (mapWidth - boxes.map.width * scale) / 2, bodyTop, scale);
        bodyHeight = Math.max(bodyHeight, placements.map.height + freeJumpHeight);
    }
    if (boxes.freeJump) {
        place('freeJump', mapX, bodyTop + (placements.map ? placements.map.height : 0) + GAP, freeJumpScale);
    }
    const footerTop = bodyTop + bodyHeight + GAP;
    placeRow(footer, footerTop, footerScale);
    // A market to the right, or a short label at the left, must not reserve an
    // empty band across the map. Keep the controls fixed and fit the network in
    // the remaining space, with the same clearance around every occupied area.
    if (boxes.map) {
        const obstacles = Object.entries(placements)
            .filter(([name]) => name !== 'map')
            .flatMap(([name, slot]) =>
                (boxes[name].parts || [boxes[name]]).map((part) => ({
                    x: slot.x + (part.x - boxes[name].x) * slot.scale,
                    y: slot.y + (part.y - boxes[name].y) * slot.scale,
                    width: part.width * slot.scale,
                    height: part.height * slot.scale,
                }))
            );
        const bounds = { x: mapX, y: PAD, width: mapWidth, height: footerTop + footerHeight - PAD };
        const fitted = fitMap(boxes.map, bounds, obstacles);
        if (fitted) place('map', fitted.x, fitted.y, fitted.scale);
    }
    return { width, height: Math.ceil(footerTop + footerHeight + PAD), placements };
}

/** Largest uniform map scale that clears the controls, preferring a centred map. */
function fitMap(map: BoardBox, bounds: BoardBox, obstacles: BoardBox[]) {
    function atScale(scale: number) {
        const w = map.width * scale,
            h = map.height * scale;
        const centre = bounds.x + (bounds.width - w) / 2;
        const xs = [
            centre,
            bounds.x,
            bounds.x + bounds.width - w,
            ...obstacles.flatMap((box) => [box.x + box.width + MAP_GAP, box.x - MAP_GAP - w]),
        ]
            .filter((x) => x >= bounds.x && x + w <= bounds.x + bounds.width + 0.001)
            .sort((a, b) => Math.abs(a - centre) - Math.abs(b - centre));
        const ys = [bounds.y, ...obstacles.map((box) => box.y + box.height + MAP_GAP)]
            .filter((y) => y >= bounds.y && y + h <= bounds.y + bounds.height + 0.001)
            .sort((a, b) => a - b);
        for (const x of xs)
            for (const y of ys) {
                if (
                    obstacles.every(
                        (box) =>
                            x + w <= box.x - MAP_GAP + 0.001 ||
                            x >= box.x + box.width + MAP_GAP - 0.001 ||
                            y + h <= box.y - MAP_GAP + 0.001 ||
                            y >= box.y + box.height + MAP_GAP - 0.001
                    )
                ) {
                    return { x, y, scale };
                }
            }
        return null;
    }
    let low = 0,
        high = Math.min(1, bounds.width / map.width, bounds.height / map.height);
    let best = atScale(high);
    if (best) return best;
    for (let i = 0; i < 20; i++) {
        const scale = (low + high) / 2;
        const candidate = atScale(scale);
        if (candidate) {
            low = scale;
            best = candidate;
        } else high = scale;
    }
    return best;
}
