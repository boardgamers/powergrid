import { BoardBox } from './board-layout';

/** Measure a slot independently of its current layout transform. Short legends
 * remain separate obstacles so empty space beside them can belong to the map. */
export function measureBoardBox(slot: SVGGraphicsElement, splitSelector?: string): BoardBox {
    const rect = slot.getBBox();
    const box: BoardBox = { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
    if (!splitSelector || !slot.querySelector(splitSelector)) return box;
    const inverse = slot.getCTM()?.inverse();
    if (!inverse) return box;
    const body: BoardBox[] = [],
        parts: BoardBox[] = [];
    function visit(element: SVGGraphicsElement) {
        if (element.matches(splitSelector!)) parts.push(measure(element));
        else if (element.querySelector(splitSelector!)) {
            for (const child of Array.from(element.children)) {
                if (typeof (child as SVGGraphicsElement).getBBox === 'function') visit(child as SVGGraphicsElement);
            }
        } else body.push(measure(element));
    }
    function measure(element: SVGGraphicsElement): BoardBox {
        const b = element.getBBox();
        const matrix = inverse!.multiply(element.getCTM()!);
        const points = [
            [b.x, b.y],
            [b.x + b.width, b.y],
            [b.x, b.y + b.height],
            [b.x + b.width, b.y + b.height],
        ].map(([x, y]) => new DOMPoint(x, y).matrixTransform(matrix));
        const x = Math.min(...points.map((p) => p.x)),
            y = Math.min(...points.map((p) => p.y));
        return {
            x,
            y,
            width: Math.max(...points.map((p) => p.x)) - x,
            height: Math.max(...points.map((p) => p.y)) - y,
        };
    }
    visit(slot);
    const visible = body.filter((b) => b.width > 0 || b.height > 0);
    if (visible.length) {
        const x = Math.min(...visible.map((b) => b.x)),
            y = Math.min(...visible.map((b) => b.y));
        parts.push({
            x,
            y,
            width: Math.max(...visible.map((b) => b.x + b.width)) - x,
            height: Math.max(...visible.map((b) => b.y + b.height)) - y,
        });
    }
    return { ...box, parts };
}
