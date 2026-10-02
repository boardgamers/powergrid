import { playerSymbolGlyph } from '@boardgamers/protocol/player-symbols';
type ColorPreferences = { colorBlind?: boolean; bgs?: { playerColors?: unknown } };
export function resolvePlayerColors(
    defaults: string[],
    players: { id: number; color?: string }[],
    preferences?: ColorPreferences
): string[] {
    const colors = [...defaults];
    const preferred = preferences?.bgs?.playerColors;
    if (!preferences?.colorBlind && !players.some((p) => p.color) && Array.isArray(preferred)) {
        preferred.slice(0, colors.length).forEach((color, i) => {
            if (typeof color === 'string' && /^#[a-f0-9]{6}$/i.test(color)) colors[i] = color;
        });
    }
    for (const player of players) if (player.color) colors[player.id] = player.color;
    return colors;
}

export function colorText(color = ''): string {
    const names: Record<string, string> = {
        limegreen: '#32cd32',
        mediumorchid: '#ba55d3',
        red: '#ff0000',
        dodgerblue: '#1e90ff',
        yellow: '#ffff00',
        brown: '#a52a2a',
    };
    const hex = names[color] ?? color;
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
