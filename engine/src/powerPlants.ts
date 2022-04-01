import { cloneDeep } from 'lodash';
import { PowerPlant, PowerPlantType } from './gamestate';

const powerPlants: PowerPlant[] = [
    { number: 3, type: PowerPlantType.Oil, cost: 2, citiesPowered: 1 },
    { number: 4, type: PowerPlantType.Coal, cost: 2, citiesPowered: 1 },
    { number: 5, type: PowerPlantType.Hybrid, cost: 2, citiesPowered: 1 },
    { number: 6, type: PowerPlantType.Garbage, cost: 1, citiesPowered: 1 },
    { number: 7, type: PowerPlantType.Oil, cost: 3, citiesPowered: 2 },
    { number: 8, type: PowerPlantType.Coal, cost: 3, citiesPowered: 2 },
    { number: 9, type: PowerPlantType.Oil, cost: 1, citiesPowered: 1 },
    { number: 10, type: PowerPlantType.Coal, cost: 2, citiesPowered: 2 },
    { number: 11, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 2 },
    { number: 12, type: PowerPlantType.Hybrid, cost: 2, citiesPowered: 2 },
    { number: 13, type: PowerPlantType.Wind, cost: 0, citiesPowered: 1 },
    { number: 14, type: PowerPlantType.Garbage, cost: 2, citiesPowered: 2 },
    { number: 15, type: PowerPlantType.Coal, cost: 2, citiesPowered: 3 },
    { number: 16, type: PowerPlantType.Oil, cost: 2, citiesPowered: 3 },
    { number: 17, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 2 },
    { number: 18, type: PowerPlantType.Wind, cost: 0, citiesPowered: 2 },
    { number: 19, type: PowerPlantType.Garbage, cost: 2, citiesPowered: 3 },
    { number: 20, type: PowerPlantType.Coal, cost: 3, citiesPowered: 5 },
    { number: 21, type: PowerPlantType.Hybrid, cost: 2, citiesPowered: 4 },
    { number: 22, type: PowerPlantType.Wind, cost: 0, citiesPowered: 2 },
    { number: 23, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 3 },
    { number: 24, type: PowerPlantType.Garbage, cost: 2, citiesPowered: 4 },
    { number: 25, type: PowerPlantType.Coal, cost: 2, citiesPowered: 5 },
    { number: 26, type: PowerPlantType.Oil, cost: 2, citiesPowered: 5 },
    { number: 27, type: PowerPlantType.Wind, cost: 0, citiesPowered: 3 },
    { number: 28, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 4 },
    { number: 29, type: PowerPlantType.Hybrid, cost: 1, citiesPowered: 4 },
    { number: 30, type: PowerPlantType.Garbage, cost: 3, citiesPowered: 6 },
    { number: 31, type: PowerPlantType.Coal, cost: 3, citiesPowered: 6 },
    { number: 32, type: PowerPlantType.Oil, cost: 3, citiesPowered: 6 },
    { number: 33, type: PowerPlantType.Wind, cost: 0, citiesPowered: 4 },
    { number: 34, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 5 },
    { number: 35, type: PowerPlantType.Oil, cost: 1, citiesPowered: 5 },
    { number: 36, type: PowerPlantType.Coal, cost: 3, citiesPowered: 7 },
    { number: 37, type: PowerPlantType.Wind, cost: 0, citiesPowered: 4 },
    { number: 38, type: PowerPlantType.Garbage, cost: 3, citiesPowered: 7 },
    { number: 39, type: PowerPlantType.Uranium, cost: 1, citiesPowered: 6 },
    { number: 40, type: PowerPlantType.Oil, cost: 2, citiesPowered: 6 },
    { number: 42, type: PowerPlantType.Coal, cost: 2, citiesPowered: 6 },
    { number: 44, type: PowerPlantType.Wind, cost: 0, citiesPowered: 5 },
    { number: 46, type: PowerPlantType.Hybrid, cost: 3, citiesPowered: 7 },
    { number: 50, type: PowerPlantType.Nuclear, cost: 0, citiesPowered: 6 },
    { number: 99, type: PowerPlantType.Nuclear, cost: 0, citiesPowered: 6 },
];

const indiaPowerPlants = cloneDeep(powerPlants).filter(pp => pp.number != 11);
// Garbage plants cost one more garbage to run, but have no additional storage.
indiaPowerPlants.forEach(pp => {
    if (pp.type == PowerPlantType.Garbage) {
        pp.storage = 2*pp.cost;
        pp.cost++;
    }
});

export {powerPlants, indiaPowerPlants};