import { playerSymbolGlyph } from '@boardgamers/protocol/player-symbols';
type ColorPreferences = {
    colorBlind?: boolean;
    preferredPlayerColors?: unknown;
    bgs?: { playerColors?: unknown };
};
const namedColors: Record<string, string> = {
    limegreen: '#32cd32',
    mediumorchid: '#ba55d3',
    red: '#ff0000',
    dodgerblue: '#1e90ff',
    yellow: '#ffff00',
    brown: '#a52a2a',
};
const hexColor = (color: unknown): string | undefined =>
    typeof color === 'string'
        ? namedColors[color] ?? (/^#[a-f0-9]{6}$/i.test(color) ? color.toLowerCase() : undefined)
        : undefined;

export function resolvePlayerColors(
    defaults: string[],
    players: { id: number; color?: string }[],
    preferences?: ColorPreferences,
    viewerIndex?: number
): string[] {
    const colors = [...defaults];
    for (const player of players) if (player.color) colors[player.id] = player.color;

    if (preferences?.colorBlind) return colors;
    const custom = preferences?.preferredPlayerColors;
    if (Array.isArray(custom)) {
        const chosen: (string | undefined)[] = colors.map(() => undefined);
        const distinct = (color: string) =>
            chosen.every((other) => {
                if (!other) return true;
                const a = hexColor(color)!;
                const b = hexColor(other)!;
                return (
                    [1, 3, 5].reduce(
                        (sum, i) => sum + (parseInt(a.slice(i, i + 2), 16) - parseInt(b.slice(i, i + 2), 16)) ** 2,
                        0
                    ) >=
                    24 ** 2
                );
            });
        const order = colors.map((_, i) => i);
        if (
            viewerIndex !== undefined &&
            Number.isInteger(viewerIndex) &&
            viewerIndex >= 0 &&
            viewerIndex < colors.length
        ) {
            order.splice(viewerIndex, 1);
            order.unshift(viewerIndex);
        }
        for (const i of order) {
            const color =
                typeof custom[i] === 'string' && /^#[a-f0-9]{6}$/i.test(custom[i]) ? hexColor(custom[i]) : undefined;
            if (color && distinct(color)) chosen[i] = color;
        }
        colors.forEach((color, i) => {
            if (!chosen[i] && distinct(color)) chosen[i] = color;
        });
        const available = [
            ...colors,
            ...defaults,
            '#da4a47',
            '#e68b32',
            '#e8c844',
            '#42a06a',
            '#4595d1',
            '#9868c5',
            '#da73aa',
            '#e8e7de',
            '#414955',
        ];
        return chosen.map((color, i) => {
            if (!color) chosen[i] = color = available.find(distinct) ?? colors[i];
            return color;
        });
    }

    // Older hosts send a whole default-filled palette; it cannot safely override a draft.
    const preferred = preferences?.bgs?.playerColors;
    if (!players.some((player) => player.color) && Array.isArray(preferred)) {
        preferred.slice(0, colors.length).forEach((color, i) => {
            if (typeof color === 'string' && /^#[a-f0-9]{6}$/i.test(color)) colors[i] = color;
        });
    }
    return colors;
}

export function colorText(color = ''): string {
    const hex = namedColors[color] ?? color;
    if (!/^#[a-f0-9]{6}$/i.test(hex)) return '#111';
    const channels = [1, 3, 5].map((i) => {
        const value = parseInt(hex.slice(i, i + 2), 16) / 255;
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
    });
    return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722 > 0.179 ? '#000' : '#fff';
}

export function playerSymbol(index: number, preferences: { bgs?: { playerSymbols?: string[] } }): string {
    return playerSymbolGlyph(preferences.bgs?.playerSymbols?.[index], String(index + 1));
}
