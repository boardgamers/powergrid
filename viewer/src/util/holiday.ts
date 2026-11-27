import type { Preferences } from '../types/ui-data';

export type HolidayDecorations = 'on' | 'calm' | 'off';

/** How a house is decorated right now: not at all, still, or with blinking lights. */
export type HolidayLook = 'none' | 'still' | 'lively';

/**
 * Christmas season, by the viewer's own local date: December 1 through January 6
 * (Epiphany), every year. No year is written down anywhere, so it comes back by itself.
 */
export function isChristmasSeason(now: Date): boolean {
    const month = now.getMonth();
    return month === 11 || (month === 0 && now.getDate() <= 6);
}

// Only the sandbox and tests move the clock; a real game always reads the device date.
let clock: () => Date = () => new Date();

export function setHolidayClock(next: () => Date): void {
    clock = next;
}

/** Whether today (by the viewer's clock) falls in the Christmas season. */
export function inHolidaySeason(): boolean {
    return isChristmasSeason(clock());
}

const NEXT_SETTING: Record<HolidayDecorations, HolidayDecorations> = { on: 'calm', calm: 'off', off: 'on' };

/** The board button cycles On -> Calm -> Off -> On. */
export function nextHolidaySetting(current: HolidayDecorations | undefined): HolidayDecorations {
    return NEXT_SETTING[current ?? 'on'];
}

function prefersReducedMotion(): boolean {
    return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

/**
 * The look for this viewer. The setting belongs to the person watching, so a player who
 * turns decorations off sees plain houses for everyone. "Reduce motion" on the device
 * always means still lights.
 */
export function holidayLook(
    preferences: Pick<Preferences, 'holidayDecorations'> | undefined,
    now: Date = clock(),
    reducedMotion: boolean = prefersReducedMotion()
): HolidayLook {
    const setting = preferences?.holidayDecorations ?? 'on';
    if (setting === 'off' || !isChristmasSeason(now)) return 'none';
    return setting === 'calm' || reducedMotion ? 'still' : 'lively';
}

// The roofline of the house drawn in House.vue (its own coordinates): the left eave,
// up over the ridge to the right eave, then back along the front gable.
const ROOFLINE: [number, number][] = [
    [3, 169.5],
    [80.9, 108.1],
    [304.8, 4],
    [395.7, 136.4],
    [187.7, 263.6],
    [80.9, 108.1],
];

const BULB_COLORS = ['#e8423b', '#f4c542', '#3fae5a', '#3d8fe0'];

export interface Bulb {
    x: number;
    y: number;
    color: string;
    /** Half the bulbs blink out of step with the other half. */
    alternate: boolean;
}

export const ROOFLINE_POINTS = ROOFLINE.map((p) => p.join(',')).join(' ');

/** A string of lights along the roofline, roughly one bulb every 52 units. */
export const BULBS: Bulb[] = (() => {
    const bulbs: Bulb[] = [];
    for (let i = 0; i < ROOFLINE.length - 1; i++) {
        const [x1, y1] = ROOFLINE[i];
        const [x2, y2] = ROOFLINE[i + 1];
        const steps = Math.max(2, Math.round(Math.hypot(x2 - x1, y2 - y1) / 52));
        for (let s = 0; s < steps; s++) {
            const t = s / steps;
            const k = bulbs.length;
            bulbs.push({
                x: x1 + (x2 - x1) * t,
                y: y1 + (y2 - y1) * t + 10,
                color: BULB_COLORS[k % BULB_COLORS.length],
                alternate: k % 2 === 1,
            });
        }
    }
    return bulbs;
})();
