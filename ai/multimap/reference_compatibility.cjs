// Mechanical compatibility only: never neural inference or tournament outcomes.
const assert = require('node:assert/strict');
const path = require('node:path');
const { isDeepStrictEqual } = require('node:util');
const { start } = require('./game.cjs');
const f = require('./features.cjs');
const { publicState, hiddenInvariant, atomicIndex, ENGINE_VERSION, SEED_NAMESPACE } = require('./reference_game.cjs');
const flatten = (menu) =>
    Object.entries(menu || {}).flatMap(([name, values]) => values.map((data) => ({ name, data })));

function screen(artifact) {
    artifact = path.resolve(artifact);
    const old = require(path.join(artifact, 'ai/core.cjs'));
    const prepare = require(path.join(artifact, 'ai/strong/population-hybrid-policy.cjs')).preparePolicy;
    const beliefs = require(path.join(artifact, 'ai/strong/sealed-policy-beliefs.cjs'));
    const rows = [];
    function check(g, tag, cell) {
        const seat = g.currentPlayers[0];
        for (const p of g.players) p.availableMoves = g.currentPlayers.includes(p.id) ? f.E.availableMoves(g, p) : null;
        const legal = f.legal(g, seat),
            state = hiddenInvariant(g, seat);
        const row = {
            cell,
            tag,
            authoritativeActions: legal.length,
            discountActive: !!g.plantDiscountActive,
            minimumLegalBid: legal.find((move) => move.name === 'Bid')?.data ?? null,
        };
        try {
            assert.equal(JSON.stringify(beliefs.publicState(g, seat)), JSON.stringify(state), 'Projection differs');
            const rebuilt = flatten(old.E.availableMoves(structuredClone(state), structuredClone(state.players[seat])));
            row.recomputedMenuEqual = isDeepStrictEqual(rebuilt, legal);
            if (!row.recomputedMenuEqual) {
                row.oldOnly = rebuilt.filter((a) => !legal.some((b) => isDeepStrictEqual(a, b)));
                row.currentOnly = legal.filter((a) => !rebuilt.some((b) => isDeepStrictEqual(a, b)));
            }
            const result = prepare({ state, player: seat, featureRevision: '4.3-strategic-correction' });
            const indices = result.moves.map((move) => atomicIndex(legal, move));
            row.preparedActions = result.moves.length;
            row.thinned = result.moves.length < legal.length;
            row.indexTranslationRequired = indices.some((value, i) => value !== i);
            row.forbiddenBuilds = result.lossFilter.forbidden.length;
            assert.throws(() => atomicIndex(legal, { name: 'Bid', data: -1 }));
            row.illegalRejected = true;
            row.hiddenProjectionInvariant = true;
            row.preparationPassed = true;
        } catch (error) {
            row.preparationPassed = false;
            row.error = error.message;
        }
        rows.push(row);
    }
    for (const players of [2, 3, 4, 5, 6])
        for (const variant of ['original', 'recharged'])
            for (const fastBid of [false, true]) {
                const cell = `Germany|${players}|${variant}|${+fastBid}`;
                const base = start({
                    map: 'Germany',
                    players,
                    variant,
                    fastBid,
                    seed: `${SEED_NAMESPACE}:compatibility:${cell}`,
                });
                check(structuredClone(base), 'initial-nomination', cell);
                const actor = base.currentPlayers[0];
                if (variant === 'recharged') {
                    const discounted = structuredClone(base);
                    discounted.players[actor].money = 1;
                    check(discounted, 'discounted-one-dollar-nomination', cell);
                }
                const bid = structuredClone(base);
                bid.players.forEach((p) => {
                    p.money = 200;
                });
                f.E.move(bid, structuredClone(f.legal(bid, actor).find((a) => a.name === 'ChoosePowerPlant')), actor);
                check(bid, 'high-bid-thinning-and-discount', cell);
                if (fastBid && bid.currentPlayers.length > 1) {
                    // Exercise noncanonical pending-set order, repaired in the archived wrapper.
                    const pending = structuredClone(bid);
                    pending.currentPlayers.reverse();
                    if (pending.currentPlayers.length > 2) pending.currentPlayers.splice(1, 1);
                    check(pending, 'sealed-noncanonical-pending-set', cell);
                }
                const plants = [...base.actualMarket, ...base.futureMarket];
                const discard = structuredClone(base);
                discard.players[actor].powerPlants = structuredClone(plants.slice(0, players === 2 ? 5 : 4));
                check(discard, 'plant-limit-discard', cell);
                const fuel = structuredClone(base);
                fuel.players[actor].coalCapacity = 0;
                fuel.players[actor].hybridCapacity = 0;
                fuel.players[actor].coalLeft = 1;
                fuel.players[actor].oilLeft = 0;
                check(fuel, 'nonhybrid-fuel-overflow-discard', cell);
                const building = structuredClone(base);
                building.phase = 'Building';
                building.round = 5;
                building.step = 2;
                building.currentPlayers = [actor];
                building.players[actor].money = 300;
                building.players[actor].cities = building.map.cities
                    .slice(0, building.citiesToEndGame - 1)
                    .map((city) => ({ name: city.name, price: 10 }));
                building.players[actor].housesLeft = 22 - building.players[actor].cities.length;
                // The actor can trigger the end with zero output while a rival can power
                // one city. This must exercise the actual strict-loss FILTER certificate.
                const rival = building.players[(actor + 1) % players];
                rival.cities = [{ name: building.map.cities.at(-1).name, price: 10 }];
                rival.powerPlants = [structuredClone(plants[0])];
                rival.coalLeft = 4;
                rival.oilLeft = 4;
                rival.garbageLeft = 4;
                rival.uraniumLeft = 4;
                check(building, 'end-threshold-build', cell);
                const resource = structuredClone(base);
                resource.phase = 'Resources';
                resource.round = 3;
                resource.currentPlayers = [actor];
                resource.players[actor].coalCapacity = 4;
                resource.players[actor].oilCapacity = 4;
                check(resource, 'resource-buy', cell);
                const powering = structuredClone(base);
                powering.phase = 'Bureaucracy';
                powering.round = 3;
                powering.currentPlayers = [actor];
                powering.players[actor].powerPlants = structuredClone(plants.slice(0, 2));
                powering.players[actor].powerPlantsNotUsed = powering.players[actor].powerPlants.map((p) => p.number);
                powering.players[actor].cities = [{ name: powering.map.cities[0].name, price: 10 }];
                powering.players[actor].coalLeft = 4;
                powering.players[actor].oilLeft = 4;
                powering.players[actor].garbageLeft = 4;
                powering.players[actor].uraniumLeft = 4;
                check(powering, 'powering', cell);
            }
    return {
        authoritativeEngineVersion: ENGINE_VERSION,
        referenceEngineDeclaredVersion: '2.0.19',
        cells: 20,
        cases: rows.length,
        preparationFailures: rows.filter((r) => !r.preparationPassed).length,
        recomputedMenuMismatches: rows.filter((r) => r.recomputedMenuEqual === false).length,
        thinnedCases: rows.filter((r) => r.thinned).length,
        hiddenChecks: rows.filter((r) => r.hiddenProjectionInvariant).length,
        fullGames: 0,
        neuralDecisions: 0,
        qualification_eligible: false,
        reserved_final_seeds_used: false,
        note: 'Synthetic structural fixtures, not reachable trajectory or neural-policy parity proof. Recomputed old menus are diagnostic; authoritative legal actions remain binding.',
        rows,
    };
}
if (require.main === module) console.log(JSON.stringify(screen(process.argv[2]), null, 2));
module.exports = { screen };
