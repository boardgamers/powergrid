import { cloneDeep } from 'lodash';
import { move as execMove, Move, Phase, setup, stripSecret } from 'powergrid-engine';
import { moveAI } from 'powergrid-engine/src/engine';
import launch from './launch';

const delayBase = 0;

function launchSelfContained(selector = '#app') {
    const strip = true;

    const emitter = launch(selector);

    let gameState = setup(5, { map: 'Japan', variant: 'recharged', showMoney: true, randomizeMap: false }, '7');

    // Dev coord-picker example (commented; uncomment + drop a board photo into
    // viewer/public/ to author city coordinates for a new map). See the picker
    // notes in CLAUDE/memory or in the engine map-authoring docs.
    //
    // import { map as fullMap } from 'powergrid-engine/src/maps/southafrica';
    // gameState.map.cities = fullMap.cities.map((c) => ({ ...c }));
    // gameState.map.connections = fullMap.connections.map((c) => ({ ...c, nodes: [...c.nodes] }));
    // gameState.map.devBackdrop = { src: '/southafrica.jpg', width: 1200, height: 863, opacity: 0.5 };
    // gameState.map.adjustRatio = [1, 1];
    // gameState.map.mapRotation = 0;
    // gameState.map.mapPosition = [0, 0];
    // gameState.map.viewBox = [1200, 863];
    // gameState.map.playerBoardsPosition = [-9999, -9999];
    // gameState.map.powerPlantMarketPosition = [-9999, -9999];
    // gameState.map.buttonsPosition = [-9999, -9999];
    // gameState.map.supplyPosition = [-9999, -9999];
    // gameState.map.roundInfoPosition = [-9999, -9999];
    // gameState.map.cityCountPosition = [-9999, -9999];
    // gameState.map.playerOrderPosition = [-9999, -9999];

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
