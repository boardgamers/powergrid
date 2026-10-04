import { expect } from 'chai';
import { BoardBox, desktopBoardLayout } from '../../src/util/board-layout';

const box = (width: number, height: number, x = 0, y = 0): BoardBox => ({ x, y, width, height });
const base = {
    cityCount: box(735, 90),
    powerPlantDeck: box(96, 92),
    powerPlantMarket: box(285, 135),
    buttons: box(150, 130),
    playerOrder: box(180, 35),
    playerBoards: box(380, 430),
    resources: box(750, 135),
    roundInfo: box(270, 115),
    map: box(760, 900, 280, 410),
};

describe('desktop board layout', () => {
    it('fits tall and wide networks, 2–6 player panels and special markets without collisions', () => {
        for (const height of [580, 780, 1040]) {
            for (const players of [2, 3, 4, 5, 6]) {
                for (const map of [box(760, 900, 280, 410), box(1100, 520, -30, 20)]) {
                    for (const extra of [
                        {},
                        { uraniumMines: box(104, 396) },
                        { freeJump: box(360, 30) },
                        { resources: box(750, 295) },
                        { resources: box(1540, 140) },
                    ] as Record<string, BoardBox>[]) {
                        const boxes = {
                            ...base,
                            map,
                            playerBoards: box(
                                players >= 5 ? 780 : 380,
                                players >= 5 ? Math.ceil(players / 2) * 110 : players * 110
                            ),
                            ...extra,
                        };
                        const result = desktopBoardLayout(boxes, 1465, height);
                        const slots = Object.entries(result.placements);
                        expect(result.height).to.be.at.most(height + 1);
                        for (const [name, slot] of slots) {
                            expect(slot.scale, name).to.be.greaterThan(0);
                            expect(slot.x, name).to.be.at.least(0);
                            expect(slot.y, name).to.be.at.least(0);
                            expect(slot.x + slot.width, name).to.be.at.most(result.width + 0.001);
                            expect(slot.y + slot.height, name).to.be.at.most(result.height);
                            for (const [otherName, other] of slots) {
                                if (name === otherName) continue;
                                const overlap =
                                    Math.min(slot.x + slot.width, other.x + other.width) - Math.max(slot.x, other.x) >
                                        0.01 &&
                                    Math.min(slot.y + slot.height, other.y + other.height) - Math.max(slot.y, other.y) >
                                        0.01;
                                expect(overlap, `${name} overlaps ${otherName}`).to.equal(false);
                            }
                        }
                    }
                }
            }
        }
    });
    it('removes unused coordinate margins without moving the network relative to itself', () => {
        const shifted = { ...base, map: { ...base.map, x: 5000, y: -1500 } };
        const a = desktopBoardLayout(base, 1465, 780).placements.map;
        const b = desktopBoardLayout(shifted, 1465, 780).placements.map;
        expect([a.x, a.y, a.width, a.height, a.scale]).to.deep.equal([b.x, b.y, b.width, b.height, b.scale]);
        const [tx, ty, scale] = b.transform.match(/-?[\d.]+/g)!.map(Number);
        expect(tx + shifted.map.x * scale).to.be.closeTo(b.x, 0.3);
        expect(ty + shifted.map.y * scale).to.be.closeTo(b.y, 0.1);
    });

    it('uses the clear space beside short income and refill labels for a tall map', () => {
        const boxes = {
            ...base,
            cityCount: { ...box(735, 90), parts: [box(735, 68), box(260, 16, 0, 74)] },
            resources: { ...box(750, 135), parts: [box(335, 28), box(750, 80, 0, 55)] },
            playerBoards: box(780, 330),
            map: box(660, 900),
        };
        const result = desktopBoardLayout(boxes, 1465, 650);
        const slots = result.placements;
        expect(slots.cityCount.y).to.equal(16);
        expect(slots.map.y).to.be.lessThan(slots.powerPlantMarket.y + slots.powerPlantMarket.height);
        expect(slots.map.y + slots.map.height).to.be.greaterThan(slots.resources.y);
        // The previous full-width bands left only 308 units for this network.
        expect(slots.map.height).to.be.greaterThan(400);
        for (const name of ['cityCount', 'resources'] as const) {
            for (const part of boxes[name].parts) {
                const slot = slots[name];
                const x = slot.x + part.x * slot.scale,
                    y = slot.y + part.y * slot.scale;
                const m = slots.map;
                expect(
                    m.x + m.width <= x ||
                        m.x >= x + part.width * slot.scale ||
                        m.y + m.height <= y ||
                        m.y >= y + part.height * slot.scale,
                    `map overlaps ${name} content`
                ).to.equal(true);
            }
        }
    });

    it('reserves the actual width of longer translated labels', () => {
        const resources = { ...box(750, 135), parts: [box(335, 28), box(750, 80, 0, 55)] };
        const short = desktopBoardLayout({ ...base, resources }, 1465, 650);
        const long = desktopBoardLayout(
            { ...base, resources: { ...resources, parts: [box(750, 28), box(750, 80, 0, 55)] } },
            1465,
            650
        );
        expect(long.placements.map.scale).to.be.at.most(short.placements.map.scale);
        const map = long.placements.map;
        expect(map.y + map.height).to.be.at.most(long.placements.resources.y - 19.99);
    });
});
