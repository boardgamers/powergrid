import type { AchievementDefinition, AchievementManifest, SeatAchievements } from '@boardgamers/protocol/engine';
import { ended, playersSortedByScore } from './engine';
import { GameState, MapName, Player, PowerPlantType } from './gamestate';

// Explicit stable IDs, not generated slugs. Match the resolved map name, never
// the requested option (which may be Random). Original/Recharged share a badge.
const mapAchievements: Record<MapName, string> = {
    Germany: 'germany-champion',
    USA: 'usa-champion',
    France: 'france-champion',
    Japan: 'japan-champion',
    Brazil: 'brazil-champion',
    'Spain & Portugal': 'spain-portugal-champion',
    India: 'india-champion',
    Italy: 'italy-champion',
    Quebec: 'quebec-champion',
    'Middle East': 'middle-east-champion',
    China: 'china-champion',
    Benelux: 'benelux-champion',
    Russia: 'russia-champion',
    'Central Europe': 'central-europe-champion',
    'Baden-Württemberg': 'baden-wurttemberg-champion',
    'Northern Europe': 'northern-europe-champion',
    Korea: 'korea-champion',
    Europe: 'europe-champion',
    'North America': 'north-america-champion',
    'South Africa': 'south-africa-champion',
    'UK & Ireland': 'uk-ireland-champion',
    Australia: 'australia-champion',
    Bremen: 'bremen-champion',
    Manhattan: 'manhattan-champion',
};

const definitions: AchievementDefinition[] = [
    { id: 'grid-champion', name: 'Grid Champion', description: 'Win a game of Power Grid.' },
    { id: 'head-to-head', name: 'Head to Head', description: 'Win a two-player game.' },
    { id: 'full-table', name: 'Full Table', description: 'Win a six-player game.' },
    ...Object.entries(mapAchievements).map(([map, id]) => ({
        id,
        name: `${map} Champion`,
        description: `Win on the ${map} map.`,
    })),
    {
        id: 'power-fifteen',
        name: 'Power Fifteen',
        description: 'Finish able to power at least 15 cities in your network.',
    },
    {
        id: 'power-eighteen',
        name: 'Power Eighteen',
        description: 'Finish able to power at least 18 cities in your network.',
    },
    {
        id: 'fully-supplied',
        name: 'Fully Supplied',
        description: 'Finish able to power every city in a network of at least 15 cities.',
    },
    {
        id: 'network-seventeen',
        name: 'Network Seventeen',
        description: 'Finish with at least 17 cities in your network.',
    },
    { id: 'network-twenty', name: 'Network Twenty', description: 'Finish with at least 20 cities in your network.' },
    { id: 'cash-reserve', name: 'Cash Reserve', description: 'Finish with at least 100 Elektro.' },
    { id: 'deep-reserves', name: 'Deep Reserves', description: 'Finish with at least 200 Elektro.' },
    {
        id: 'wind-farm',
        name: 'Wind Farm',
        description: 'Finish owning wind plants with a combined capacity of at least 8 cities.',
    },
    {
        id: 'atomic-power',
        name: 'Atomic Power',
        description:
            'Finish owning uranium-fuelled power plants with a combined capacity of at least 8 cities. Australian uranium mines do not count.',
    },
];

export function achievementDefinitions(): AchievementManifest {
    // A host may cache or modify its copy without changing future evaluations.
    return { revision: 2, achievements: definitions.map((definition) => ({ ...definition })) };
}

function tied(a: Player, b: Player): boolean {
    return a.citiesPowered === b.citiesPowered && a.money === b.money && a.cities.length === b.cities.length;
}

/** Evaluate only authoritative final state; BGS additionally gates cancelled tables and account eligibility. */
export function achievements(data: GameState): SeatAchievements[] {
    if (
        !ended(data) ||
        data.newTurn === false ||
        data.analysisMoney ||
        data.achievementAnalysis ||
        data.players.length < 2
    )
        return [];

    // Keep bots and dropped players in the standings: never promote a human who lost to one.
    const leader = playersSortedByScore(data)[0];
    const results: SeatAchievements[] = [];
    data.players.forEach((player, seat) => {
        if (player.isAI || player.isDropped) return;
        const win = tied(player, leader);
        const capacity = (type: PowerPlantType) =>
            player.powerPlants
                .filter((plant) => plant.type === type)
                .reduce((sum, plant) => sum + plant.citiesPowered, 0);
        const earned: string[] = [];
        if (win) {
            earned.push('grid-champion');
            if (data.players.length === 2) earned.push('head-to-head');
            if (data.players.length === 6) earned.push('full-table');
            const mapAchievement = Object.prototype.hasOwnProperty.call(mapAchievements, data.map.name)
                ? mapAchievements[data.map.name as MapName]
                : undefined;
            if (mapAchievement) earned.push(mapAchievement);
        }
        if (player.citiesPowered >= 15) earned.push('power-fifteen');
        if (player.citiesPowered >= 18) earned.push('power-eighteen');
        if (player.cities.length >= 15 && player.citiesPowered === player.cities.length) earned.push('fully-supplied');
        if (player.cities.length >= 17) earned.push('network-seventeen');
        if (player.cities.length >= 20) earned.push('network-twenty');
        if (player.money >= 100) earned.push('cash-reserve');
        if (player.money >= 200) earned.push('deep-reserves');
        if (capacity(PowerPlantType.Wind) >= 8) earned.push('wind-farm');
        if (data.map.name !== 'Australia' && capacity(PowerPlantType.Uranium) >= 8) earned.push('atomic-power');
        results.push({ seat, earned, outcome: win ? 'win' : 'loss' });
    });
    return results;
}
