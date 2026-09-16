const assert = require('node:assert/strict');
const { test } = require('node:test');
require('../../../engine/node_modules/ts-node').register({
    transpileOnly: true,
    compiler: require.resolve('typescript'),
    compilerOptions: { module: 'CommonJS', moduleResolution: 'Node', target: 'ES2022', importHelpers: false },
});
const { createTutorial } = require('@boardgamers/protocol/tutorial');
const { stripSecret, playersSortedByScore } = require('../../../engine/src/engine');
const { lessons } = require('../../src/tutorial/lessons');
const answer = (answer) => ({ kind: 'answer', answer });
const play = (name, data) => ({ kind: 'move', move: { name, data } });
function actionFor(lesson, snapshot) {
    const step = lesson.steps[snapshot.step].id;
    const game = snapshot.state.game;
    const choices = lesson.choices(snapshot.state, step);
    if (choices.length === 1) return choices[0].action;
    const correct = { price: '$3', route: '$12', order: 'You', 'second-space': 'No', market: 'All 6', predict: 'Ada' };
    if (correct[step]) return answer(correct[step]);
    if (lesson.id === 'auctions')
        return step === 'choose' ? play('ChoosePowerPlant', 4) : play('Bid', step === 'open' ? 4 : 6);
    if (lesson.id === 'resources' && step !== 'done') return play('BuyResource', { resource: 'coal' });
    if (lesson.id === 'income' && ['coal', 'wind'].includes(step))
        return play(
            'UsePowerPlant',
            game.players[0].availableMoves.UsePowerPlant.find((p) => p.powerPlant === (step === 'coal' ? 4 : 13))
        );
    if (lesson.id === 'upgrades') return step === 'buy' ? play('ChoosePowerPlant', 25) : play('DiscardPowerPlant', 4);
    if (['first', 'second', 'third', 'seventh', 'trigger'].includes(step)) {
        const names = { first: 'Essen', second: 'Duisburg', third: 'Dusseldorf', seventh: 'Kassel' };
        const offered = game.players[0].availableMoves.Build;
        const data = step === 'trigger' ? offered[0] : offered.find((c) => c.name === names[step]);
        assert.ok(data, `${lesson.id}/${step}: city must be offered by the engine`);
        return play('Build', data);
    }
    return play('Pass', true);
}
function memory() {
    const entries = new Map();
    return { getItem: (key) => entries.get(key) ?? null, setItem: (key, value) => entries.set(key, value) };
}
for (const lesson of lessons)
    test(`${lesson.id}: legal walkthrough, rewind and reload`, async () => {
        const storage = memory();
        const controller = await createTutorial({ ...lesson, storage });
        let actions = 0;
        while (!controller.snapshot.completed && ++actions < 30) {
            const before = controller.snapshot;
            const ok = before.canContinue
                ? await controller.continue()
                : await controller.play(actionFor(lesson, before));
            assert.equal(ok, true, `${lesson.id}/${lesson.steps[before.step].id}: ${controller.snapshot.error}`);
            const game = controller.snapshot.state.game;
            for (const resource of ['coal', 'oil', 'garbage', 'uranium']) {
                assert.ok(game[resource + 'Supply'] >= 0, `${resource} supply cannot be negative`);
                assert.ok(game[resource + 'Market'] >= 0);
                assert.equal(
                    game[resource + 'Supply'] +
                        game[resource + 'Market'] +
                        game.players.reduce((n, p) => n + p[resource + 'Left'], 0),
                    resource === 'uranium' ? 12 : 24
                );
            }
            const hidden = stripSecret(game, 0);
            assert.deepEqual(hidden.powerPlantsDeck, []);
            assert.equal(hidden.seed, 'secret');
            assert.deepEqual(hidden.hiddenLog, []);
            for (const p of game.players) {
                assert.ok(p.money >= 0);
                assert.equal(new Set(p.cities.map((c) => c.name)).size, p.cities.length);
                assert.ok(p.cities.every((c) => game.map.cities.some((m) => m.name === c.name)));
            }
            // Every checkpoint, not only a completed chapter, must survive a reload.
            const restored = await createTutorial({ ...lesson, storage });
            assert.deepEqual(restored.snapshot.state, controller.snapshot.state);
            assert.equal(restored.snapshot.step, controller.snapshot.step);
            restored.destroy();
        }
        assert.equal(controller.snapshot.completed, true);
        assert.equal(controller.snapshot.canContinue, false);
        const game = controller.snapshot.state.game;
        if (lesson.id === 'auctions')
            assert.deepEqual(
                game.players.map((p) => p.powerPlants.length),
                [1, 1, 1]
            );
        if (lesson.id === 'resources') assert.equal(game.players[0].money, 40);
        if (lesson.id === 'network') assert.equal(game.players[0].money, 18);
        if (lesson.id === 'income') {
            assert.equal(game.players[0].money, 51);
            assert.deepEqual(game.playerOrder, [0, 1, 2]);
        }
        if (lesson.id === 'upgrades')
            assert.deepEqual(
                game.players[0].powerPlants.map((p) => p.number),
                [8, 13, 25]
            );
        if (lesson.id === 'steps') {
            assert.equal(game.step, 3);
            assert.equal(game.actualMarket.length, 6);
            assert.equal(game.futureMarket.length, 0);
        }
        if (lesson.id === 'final-round') {
            assert.equal(playersSortedByScore(game)[0].id, 1);
            assert.deepEqual(
                game.players.map((p) => p.citiesPowered),
                [15, 16, 5]
            );
        }
        await controller.previousStep();
        assert.equal(controller.snapshot.completed, false);
        await controller.restart();
        assert.deepEqual(controller.snapshot.state, lesson.initialState());
        controller.destroy();
    });
test('wrong answers and unrelated or illegal moves preserve the game', async () => {
    const lesson = lessons.find((l) => l.id === 'resources');
    const controller = await createTutorial(lesson);
    await controller.continue();
    const before = JSON.stringify(controller.snapshot.state);
    assert.equal(await controller.play(play('BuyResource', { resource: 'uranium' })), false);
    assert.equal(JSON.stringify(controller.snapshot.state), before);
    await controller.play(play('BuyResource', { resource: 'coal' }));
    await controller.play(play('BuyResource', { resource: 'coal' }));
    assert.equal(await controller.play(answer('$2')), false);
    assert.ok(controller.snapshot.error);
    assert.equal(await controller.play(answer('$3')), true);
    assert.match(controller.snapshot.feedback, /^Correct!/);
    controller.destroy();
});
