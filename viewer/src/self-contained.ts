import { cloneDeep } from 'lodash';
import { move as execMove, Move, setup, stripSecret } from 'powergrid-engine';
import { moveAI } from 'powergrid-engine/src/engine';
import launch from './launch';

const delayBase = 0;

function launchSelfContained(selector = '#app') {
    const strip = false;

    const emitter = launch(selector);

    let gameState = setup(6, { map: 'Germany', variant: 'recharged', showMoney: true });

    for (let i = 0; i < gameState.players.length; i++) {
        gameState.players[i].name = `Player ${i + 1}`;
    }

    let playerIndex = 0;

    for (const player of gameState.players) {
        if (player.id != playerIndex) player.isAI = true;
    }

    emitter.on('move', async (move: Move) => {
        console.log('move received', move);
        gameState = execMove(gameState, move, playerIndex);
        console.log('new game state', gameState);

        emitter.emit('state', cloneDeep(strip ? stripSecret(gameState, playerIndex) : gameState));

        let delay = delayBase;
        while (gameState.players.some((pl) => pl.isAI && pl.availableMoves)) {
            gameState = moveAI(
                gameState,
                gameState.players.findIndex((pl) => pl.isAI && pl.availableMoves)
            );
            let newState = cloneDeep(strip ? stripSecret(gameState, playerIndex) : gameState);
            console.log('new game state', newState);
            setTimeout(() => emitter.emit('state', newState), delay);
            delay += delayBase;
        }

        console.log('available moves', gameState.players[playerIndex].availableMoves);
    });

    emitter.on('fetchSate', () =>
        emitter.emit('state', cloneDeep(strip ? stripSecret(gameState, playerIndex) : gameState))
    );

    emitter.emit('player', { index: playerIndex });
    emitter.emit('state', cloneDeep(strip ? stripSecret(gameState, playerIndex) : gameState));

    let delay = delayBase;
    while (gameState.players.some((pl) => pl.isAI && pl.availableMoves)) {
        gameState = moveAI(
            gameState,
            gameState.players.findIndex((pl) => pl.isAI && pl.availableMoves)
        );
        let newState = cloneDeep(strip ? stripSecret(gameState, playerIndex) : gameState);
        setTimeout(() => emitter.emit('state', newState), delay);
        delay += delayBase;
    }

    console.log('available moves', gameState.players[playerIndex].availableMoves);
}

export default launchSelfContained;
