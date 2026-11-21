import { expect } from 'chai';
import {
    centreOn,
    clampZoom,
    IDENTITY,
    isZoomed,
    MapZoom,
    MAP_ZOOM_MAX,
    minimapBox,
    pan,
    visibleRect,
    zoomAt,
    zoomCentre,
    zoomTransform,
} from '../../src/util/map-zoom';

const rect = { x: 280, y: 410, width: 760, height: 900 };
const apply = (z: MapZoom, p: [number, number]): [number, number] => [z.k * p[0] + z.x, z.k * p[1] + z.y];

/** The zoomed map must still cover its own box on every side. */
function covers(z: MapZoom) {
    const [l, t] = apply(z, [rect.x, rect.y]);
    const [r, b] = apply(z, [rect.x + rect.width, rect.y + rect.height]);
    expect(l).to.be.at.most(rect.x + 1e-6);
    expect(t).to.be.at.most(rect.y + 1e-6);
    expect(r).to.be.at.least(rect.x + rect.width - 1e-6);
    expect(b).to.be.at.least(rect.y + rect.height - 1e-6);
}

describe('map zoom', () => {
    it('starts at the fitted size and draws no transform there', () => {
        expect(isZoomed(IDENTITY)).to.equal(false);
        expect(zoomTransform(IDENTITY)).to.equal(undefined);
    });

    it('keeps the point under the cursor still', () => {
        const p: [number, number] = [500, 700];
        const z = zoomAt(IDENTITY, 2, p[0], p[1], rect);
        expect(z.k).to.equal(2);
        const [x, y] = apply(z, p);
        expect(x).to.be.closeTo(p[0], 1e-9);
        expect(y).to.be.closeTo(p[1], 1e-9);
    });

    it('never zooms out past the fit, nor in past the maximum', () => {
        expect(zoomAt(IDENTITY, 0.5, 500, 700, rect)).to.deep.equal(IDENTITY);
        let z = IDENTITY;
        for (let i = 0; i < 30; i++) z = zoomCentre(z, 1.25, rect);
        expect(z.k).to.equal(MAP_ZOOM_MAX);
        covers(z);
    });

    it('returns exactly to the fit when zoomed back out', () => {
        let z = zoomAt(IDENTITY, 3, 900, 1200, rect);
        z = zoomAt(z, 1 / 3, 400, 500, rect);
        expect(z).to.deep.equal(IDENTITY);
    });

    it('cannot pan the board off into empty space', () => {
        const z = zoomCentre(IDENTITY, 2, rect);
        for (const [dx, dy] of [
            [10000, 0],
            [-10000, 0],
            [0, 10000],
            [0, -10000],
            [5000, -5000],
        ]) {
            covers(pan(z, dx, dy, rect));
        }
        // Zooming at a corner is clamped too.
        covers(zoomAt(IDENTITY, 2.5, rect.x, rect.y, rect));
        covers(zoomAt(IDENTITY, 2.5, rect.x + rect.width, rect.y + rect.height, rect));
    });

    it('boxes exactly what is on screen, and centres a tapped point', () => {
        const z = zoomAt(IDENTITY, 2, 600, 800, rect);
        const v = visibleRect(z, rect);
        expect(v.width).to.be.closeTo(rect.width / 2, 1e-9);
        const [x, y] = apply(z, [v.x, v.y]);
        expect(x).to.be.closeTo(rect.x, 1e-9);
        expect(y).to.be.closeTo(rect.y, 1e-9);
        const c = centreOn(z, 700, 900, rect);
        const [cx, cy] = apply(c, [700, 900]);
        expect(cx).to.be.closeTo(rect.x + rect.width / 2, 1e-9);
        expect(cy).to.be.closeTo(rect.y + rect.height / 2, 1e-9);
        covers(centreOn(z, rect.x, rect.y, rect)); // a corner still clamps
    });

    it('sizes the minimap between its limits, in the bottom-left corner', () => {
        for (const px of [0.27, 1, 2]) {
            const m = minimapBox(rect, px);
            const longPx = Math.max(m.width, m.height) * px;
            expect(longPx).to.be.within(72 - 1e-9, 128 + 1e-9);
            expect(m.x).to.be.above(rect.x);
            expect(m.y + m.height).to.be.below(rect.y + rect.height);
            expect(m.width / m.height).to.be.closeTo(rect.width / rect.height, 1e-9);
        }
    });

    it('does not pan at the fitted size', () => {
        expect(pan(IDENTITY, 120, -80, rect)).to.deep.equal(IDENTITY);
        expect(clampZoom({ k: 1, x: 50, y: 50 }, rect)).to.deep.equal(IDENTITY);
    });
});
