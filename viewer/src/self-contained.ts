import { cloneDeep } from 'lodash';
import { move as execMove, Move, Phase, setup, stripSecret } from 'powergrid-engine';
import { moveAI } from 'powergrid-engine/src/engine';
import launch from './launch';

const delayBase = 0;

function launchSelfContained(selector = '#app') {
    const strip = true;

    const emitter = launch(selector);

    let gameState = setup(3, { map: 'Brazil', variant: 'original', showMoney: true, randomizeMap: true }, '3');

    // gameState.map.viewBox = [1480, 1060];
    // gameState.map.playerOrderPosition = [1160, 140];
    // gameState.map.cityCountPosition = [0, 0];
    // gameState.map.powerPlantMarketPosition = [745, 0];
    // gameState.map.mapPosition = [0, 100];
    // gameState.map.buttonsPosition = [1305, 0];
    // gameState.map.playerBoardsPosition = [1105, 200];
    // gameState.map.roundInfoPosition = [20, 590];
    // gameState.map.supplyPosition = [0, 720];

    // gameState.map.adjustRatio = [1, 1];
    // gameState.map.cities = gameState.map.cities.map(city => ({
    //     ...city,
    //     x: city.x * gameState.map.adjustRatio![0],
    //     y: city.y * gameState.map.adjustRatio![1]
    // }));

    // gameState.map.cities = gameState.map.cities.map(city => ({
    //     ...city,
    //     x: city.y,
    //     y: 600 - city.x
    // }));

    for (let i = 0; i < gameState.players.length; i++) {
        gameState.players[i].name = `Player ${i + 1}`;
    }

    let playerIndex = 1;

    for (const player of gameState.players) {
        if (player.id != playerIndex) player.isAI = true;
    }

    emitter.on('move', async (move: Move) => {
        setTimeout(() => {
            console.log('move received', move);
            gameState = execMove(gameState, move, playerIndex);
            console.log('new game state', gameState);

            emitter.emit('state', cloneDeep(strip ? stripSecret(gameState, playerIndex) : gameState));

            let delay = delayBase;
            const moveAIAux = () => {
                if (gameState.players.some((pl) => pl.isAI && pl.availableMoves)) {
                    gameState = moveAI(
                        gameState,
                        gameState.players.findIndex((pl) => pl.isAI && pl.availableMoves)
                    );
                    let newState = cloneDeep(strip ? stripSecret(gameState, playerIndex) : gameState);
                    console.log('new game state', newState);
                    emitter.emit('state', newState);
                    setTimeout(moveAIAux, gameState.phase == Phase.Bureaucracy ? delay : 0);
                }
            };

            setTimeout(moveAIAux, gameState.phase == Phase.Bureaucracy ? delay : 0);

            console.log('available moves', gameState.players[playerIndex].availableMoves);
        }, 100);
    });

    emitter.on('fetchState', () => {
        emitter.emit('state', cloneDeep(strip ? stripSecret(gameState, playerIndex) : gameState));
    });

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
