import { expect } from 'chai';
import 'mocha';
import { availableMoves, canStoreFuel, fuelOverCapacity, maxStorable } from './available-moves';
import { calculateMaxCitiesPowered, ended, move, moveAI, setup, updatePlayerCapacity } from './engine';
import { GameState, MapName, Phase, Player, PowerPlant, PowerPlantType, ResourceType, Variant } from './gamestate';
import { Move, MoveName } from './move';
import { alternatePowerPlants, powerPlants } from './powerPlants';

const alternate = (num: number): PowerPlant => ({ ...alternatePowerPlants.find((p) => p.number == num)! });

// Every plant a freshly set up game can still see: market, future market and deck.
function visiblePlants(G: GameState): PowerPlant[] {
    return [...G.actualMarket, ...G.futureMarket, ...G.powerPlantsDeck];
}

function givePlants(player: Player, numbers: number[]) {
    player.powerPlants = numbers.map(alternate);
    player.powerPlantsNotUsed = [...numbers];
    updatePlayerCapacity(player);
}

describe('Alternate power plant deck', () => {
    it('should deal from the alternate deck on Europe and North America', () => {
        const cases: [MapName, Variant][] = [
            ['Europe', 'recharged'],
            ['North America', 'recharged'],
            ['North America', 'original'],
        ];
        for (const [map, variant] of cases) {
            for (const numPlayers of [2, 3, 4, 5, 6]) {
                const G = setup(numPlayers, { map, variant, alternatePowerPlants: true }, `alt-${map}-${numPlayers}`);
                const label = `${map} ${variant} ${numPlayers}P`;

                expect(G.options.alternatePowerPlants, label).to.be.true;
                for (const plant of visiblePlants(G)) {
                    expect(plant, `${label} plant ${plant.number}`).to.deep.equal(alternate(plant.number));
                }
                expect(G.powerPlantsDeck[G.powerPlantsDeck.length - 1].type, label).to.equal(PowerPlantType.Step3);
                G.players.forEach((p) => expect(p.garbageOilHybridCapacity, label).to.equal(0));
            }
        }
    });

    it('should keep the standard deck when the option is off', () => {
        const G = setup(4, { map: 'Europe', variant: 'recharged' }, 'alt-off');
        for (const plant of visiblePlants(G)) {
            expect(plant).to.deep.equal(powerPlants.find((p) => p.number == plant.number));
        }
        expect(G.options).to.not.have.property('alternatePowerPlants');
        expect(G.players[0]).to.not.have.property('garbageOilHybridCapacity');
    });

    it('should ignore the option on maps that do not support it', () => {
        const withOption = setup(4, { map: 'USA', variant: 'original', alternatePowerPlants: true }, 'alt-usa');
        const without = setup(4, { map: 'USA', variant: 'original' }, 'alt-usa');

        expect(withOption).to.deep.equal(without);
    });

    it('should rebuild the same deck from the stored options', () => {
        const G = setup(4, { map: 'North America', variant: 'original', alternatePowerPlants: true }, 'alt-replay');
        const again = setup(4, G.options, G.seed);

        expect(again.actualMarket).to.deep.equal(G.actualMarket);
        expect(again.futureMarket).to.deep.equal(G.futureMarket);
        expect(again.powerPlantsDeck).to.deep.equal(G.powerPlantsDeck);
    });

    it('should share the garbage/oil hybrid tank between garbage and oil', () => {
        const G = setup(3, { map: 'Europe', variant: 'recharged', alternatePowerPlants: true }, 'alt-storage');
        const player = G.players[0];
        // Plant 8 burns 3 garbage/oil (tank of 6); plant 10 burns 2 oil (holds 4).
        givePlants(player, [8, 10]);
        expect(player.garbageOilHybridCapacity).to.equal(6);
        expect(player.oilCapacity).to.equal(4);
        expect(player.garbageCapacity).to.equal(0);

        expect(canStoreFuel(player, 0, 10, 0), '4 oil in plant 10, 6 in the tank').to.be.true;
        expect(canStoreFuel(player, 0, 11, 0)).to.be.false;
        expect(canStoreFuel(player, 0, 4, 6), 'tank full of garbage').to.be.true;
        expect(canStoreFuel(player, 0, 7, 3), 'tank split 3/3').to.be.true;
        expect(canStoreFuel(player, 0, 8, 3)).to.be.false;
        expect(canStoreFuel(player, 1, 0, 0), 'no plant takes coal').to.be.false;

        // Buying: room for garbage and oil until the tank is full.
        G.phase = Phase.Resources;
        player.money = 200;
        player.garbageLeft = 3;
        player.oilLeft = 6;
        const offered = (availableMoves(G, player)[MoveName.BuyResource] ?? []).map((r) => r.resource);
        expect(offered).to.include(ResourceType.Garbage);
        expect(offered).to.include(ResourceType.Oil);
        expect(offered).to.not.include(ResourceType.Coal);

        player.oilLeft = 7;
        const full = (availableMoves(G, player)[MoveName.BuyResource] ?? []).map((r) => r.resource);
        expect(full).to.not.include(ResourceType.Garbage);
        expect(full).to.not.include(ResourceType.Oil);
    });

    it('should work out what to discard when the shared tank overflows', () => {
        const G = setup(3, { map: 'Europe', variant: 'recharged', alternatePowerPlants: true }, 'alt-overflow');
        const player = G.players[0];
        // After losing a garbage plant: plant 8 (tank 6) and plant 10 (4 oil).
        givePlants(player, [8, 10]);
        player.garbageLeft = 5;
        player.oilLeft = 6;

        expect(fuelOverCapacity(player)).to.deep.equal([ResourceType.Oil, ResourceType.Garbage]);
        expect(maxStorable(player, ResourceType.Garbage)).to.equal(4);
        expect(maxStorable(player, ResourceType.Oil)).to.equal(5);

        G.phase = Phase.Auction;
        expect(availableMoves(G, player)[MoveName.DiscardResources]).to.deep.equal([
            ResourceType.Oil,
            ResourceType.Garbage,
        ]);

        // Only oil that sits in its own plant: nothing to discard.
        player.garbageLeft = 6;
        player.oilLeft = 4;
        expect(fuelOverCapacity(player)).to.deep.equal([]);
    });

    it('should offer every garbage/oil split when powering a garbage/oil hybrid', () => {
        const G = setup(3, { map: 'Europe', variant: 'recharged', alternatePowerPlants: true }, 'alt-power');
        G.phase = Phase.Bureaucracy;
        G.currentPlayers = [0];
        const player = G.players[0];
        givePlants(player, [8]);
        player.garbageLeft = 2;
        player.oilLeft = 2;

        const uses = availableMoves(G, player)[MoveName.UsePowerPlant]!;
        expect(uses.map((u) => u.resourcesSpent)).to.deep.equal([
            [ResourceType.Garbage, ResourceType.Garbage, ResourceType.Oil],
            [ResourceType.Garbage, ResourceType.Oil, ResourceType.Oil],
        ]);

        player.availableMoves = availableMoves(G, player);
        const after = move(
            G,
            {
                name: MoveName.UsePowerPlant,
                data: { powerPlant: 8, resourcesSpent: uses[1].resourcesSpent, citiesPowered: 2 },
            } as Move,
            0
        );
        expect(after.players[0].garbageLeft).to.equal(1);
        expect(after.players[0].oilLeft).to.equal(0);
    });

    it('should count garbage/oil hybrids when scoring cities powered', () => {
        const G = setup(3, { map: 'Europe', variant: 'recharged', alternatePowerPlants: true }, 'alt-score');
        const player = G.players[0];
        givePlants(player, [8, 10]);
        player.cities = Array.from({ length: 10 }, (_, i) => ({ name: `City ${i}`, position: 0 }));

        // Plant 8 (3 garbage/oil -> 2) and plant 10 (2 oil -> 2) need 5 fuel between them.
        player.garbageLeft = 1;
        player.oilLeft = 4;
        expect(calculateMaxCitiesPowered(G, player)).to.equal(4);

        player.oilLeft = 3;
        expect(calculateMaxCitiesPowered(G, player)).to.equal(2);
    });

    for (const [map, variant] of [
        ['Europe', 'recharged'],
        ['North America', 'original'],
    ] as [MapName, Variant][]) {
        it(`should play a whole bot game on ${map} with the alternate deck and replay it`, () => {
            let G = setup(4, { map, variant, alternatePowerPlants: true }, `alt-bots-${map}`);
            G.players.forEach((p, i) => {
                p.name = `AI ${i}`;
                p.isAI = true;
            });

            for (let turn = 0; turn < 5000 && !ended(G) && G.currentPlayers.length > 0; turn++) {
                G = moveAI(G, G.currentPlayers[0]);
            }
            expect(ended(G), 'game finished').to.be.true;

            let replay = setup(4, G.options, G.seed);
            replay.players.forEach((p, i) => {
                p.name = `AI ${i}`;
                p.isAI = true;
            });
            for (const item of G.log) {
                if (item.type === 'move') {
                    replay = move(replay, item.move, item.player);
                }
            }
            expect(replay.players.map((p) => p.citiesPowered)).to.deep.equal(G.players.map((p) => p.citiesPowered));
            expect(replay.players.map((p) => p.money)).to.deep.equal(G.players.map((p) => p.money));
        });
    }
});
