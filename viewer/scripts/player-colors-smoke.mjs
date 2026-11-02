import assert from 'node:assert/strict';

export async function checkPlayerColors(page, engine) {
    let state = engine.setup(3, { map: 'Germany', chooseColors: true }, 'custom-colours', undefined, undefined, [
        '#12ab34',
        null,
        null,
    ]);
    while (state.phase === engine.Phase.ColorSelection) {
        const seat = state.currentPlayers[0];
        const choices = state.players[seat].availableMoves.ChooseColor;
        state = engine.move(state, { name: 'ChooseColor', data: choices.at(-1) }, seat);
    }
    state = JSON.parse(JSON.stringify(state));
    state.players.forEach((player, i) => {
        player.name = ['You', 'Ada Lovelace', 'Bob'][i];
    });
    await page.evaluate((state) => {
        host.emit('preferences', { sound: false, colorBlind: false, preferredPlayerColors: ['#12ab34', null, null] });
        host.emit('player', { index: 0 });
        host.emit('state', state);
    }, state);
    const colours = () =>
        page
            .locator('.player-board')
            .evaluateAll((boards) =>
                Object.fromEntries(
                    boards.map((board) => [
                        board.querySelector('[data-bgs-player]').getAttribute('data-bgs-player'),
                        board.querySelectorAll(':scope > rect')[1].getAttribute('fill'),
                    ])
                )
            );
    await page.waitForFunction(() =>
        [...document.querySelectorAll('.player-board')].some(
            (board) => board.querySelectorAll(':scope > rect')[1]?.getAttribute('fill') === '#12ab34'
        )
    );
    assert.deepEqual(await colours(), { 0: '#12ab34', 1: state.players[1].color, 2: state.players[2].color });
    await page.evaluate(() => {
        host.emit('preferences', { sound: false, preferredPlayerColors: ['#12ab34', '#12ab34', null] });
        host.emit('player', { index: 1 });
    });
    await page.waitForFunction(
        () =>
            [...document.querySelectorAll('.player-board')]
                .find((board) => board.querySelector('[data-bgs-player="1"]'))
                ?.querySelectorAll(':scope > rect')[1]
                ?.getAttribute('fill') === '#12ab34'
    );
    assert.deepEqual(await colours(), { 0: state.players[0].color, 1: '#12ab34', 2: state.players[2].color });
    // A profile update must repaint even when the viewing seat and game state stay the same.
    await page.evaluate(() =>
        host.emit('preferences', { sound: false, preferredPlayerColors: [null, '#ab12cd', null] })
    );
    await page.waitForFunction(() =>
        [...document.querySelectorAll('.player-board')].some(
            (board) => board.querySelectorAll(':scope > rect')[1]?.getAttribute('fill') === '#ab12cd'
        )
    );
    assert.deepEqual(await colours(), { 0: state.players[0].color, 1: '#ab12cd', 2: state.players[2].color });
    await page.evaluate(() => host.emit('preferences', { sound: false, preferredPlayerColors: [null, null, null] }));
    await page.waitForFunction(
        () =>
            ![...document.querySelectorAll('.player-board')].some(
                (board) => board.querySelectorAll(':scope > rect')[1]?.getAttribute('fill') === '#ab12cd'
            )
    );
    assert.deepEqual(await colours(), Object.fromEntries(state.players.map((p) => [p.id, p.color])));
}
