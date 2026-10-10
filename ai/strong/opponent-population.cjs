const { seedrandom } = require('../core.cjs');

const FROZEN_ROLES = ['frozen0', 'frozen1', 'frozen2'];
const POPULATION = ['economic', 'heuristic', 'rush', 'search_geo', ...FROZEN_ROLES,
    'snapshot0', 'snapshot1', 'snapshot2'];
const POPULATION_MODES = ['population_homogeneous', 'population_heterogeneous'];
const isNeuralRole = role => role === 'learner' || /^snapshot[0-2]$/.test(role) || FROZEN_ROLES.includes(role);

function populationRoles(mode, count, learnerSeat, seed, id) {
    if (!POPULATION_MODES.includes(mode)) throw Error('Unknown population mode');
    if (!Number.isInteger(count) || count < 2 || count > 6 || !Number.isInteger(learnerSeat) ||
        learnerSeat < 0 || learnerSeat >= count) throw Error('Invalid player count or learner seat');
    // Retain the previous 1/8 self-play fraction. Non-self-play tables sample
    // identical marginal opponent distributions in both experimental arms.
    if (seedrandom(`${seed}-population-selfplay-${id}`)() < 1 / 8)
        return Array(count).fill('learner');
    return Array.from({ length: count }, (_, seat) => {
        if (seat === learnerSeat) return 'learner';
        const relative = (seat - learnerSeat + count) % count - 1;
        const slot = mode === 'population_homogeneous' ? 0 : relative;
        return POPULATION[Math.floor(seedrandom(`${seed}-population-role-${id}-${slot}`)() * POPULATION.length)];
    });
}

module.exports = { FROZEN_ROLES, POPULATION, POPULATION_MODES, isNeuralRole, populationRoles };
