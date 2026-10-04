export interface BoardBox {
    x: number;
    y: number;
    width: number;
    height: number;
}

export interface BoardPlacement extends BoardBox {
    scale: number;
    transform: string;
}

const PAD = 16;
const GAP = 20;
const rounded = (n: number) => Number(n.toFixed(4));

/** Pack measured game components; decorative geography never participates. */
export function desktopBoardLayout(boxes: Record<string, BoardBox>, width: number, targetHeight: number) {
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
    const chrome = Math.min(1, Math.max(0.6, (targetHeight - 180 - PAD * 2 - GAP * 2) / Math.max(1, fixedHeight)));
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
    function placeRow(names: string[], y: number, scale: number) {
        const height = rowHeight(names, scale);
        const occupied = names.reduce((n, name) => n + boxes[name].width * scale, 0);
        const gap = names.length > 1 ? (usable - occupied) / (names.length - 1) : 0;
        let x = PAD;
        for (const name of names) {
            place(name, x, y + (height - boxes[name].height * scale) / 2, scale);
            x += boxes[name].width * scale + gap;
        }
    }
    placeRow(header, PAD, headerScale);

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
    return { width, height: Math.ceil(footerTop + footerHeight + PAD), placements };
}
