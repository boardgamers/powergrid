import { cloneDeep } from 'lodash';
import { move as execMove, Move, Phase, setup, stripSecret } from 'powergrid-engine';
import { moveAI } from 'powergrid-engine/src/engine';
import launch from './launch';

const delayBase = 0;

function launchSelfContained(selector = '#app') {
    const strip = true;

    const emitter = launch(selector);

    let gameState = setup(5, { map: 'North America', variant: 'recharged', showMoney: true, randomizeMap: false }, '7');

    // Dev coord-picker: drop a printed-board photo into viewer/public/, then
    // uncomment + adjust below to overlay it behind the map. Click cities on
    // the photo; ready-to-paste `{ name, region, x, y }` lines log to the
    // browser console.
    //
    // For an EXISTING map, import the map file and replace cities +
    // connections with the originals — this bypasses the engine's setup-time
    // `adjustRatio` scaling and the 5-of-7 region filter, so you see all
    // cities in their authoring coord space:
    //   import { map as fullMap } from 'powergrid-engine/src/maps/northamerica';
    //   gameState.map.cities = fullMap.cities.map((c) => ({ ...c }));
    //   gameState.map.connections = fullMap.connections.map((c) => ({ ...c, nodes: [...c.nodes] }));
    //
    // gameState.map.devBackdrop = { src: '/board.jpg', width: 2000, height: 1716, opacity: 0.5 };
    // gameState.map.adjustRatio = [1, 1];
    // gameState.map.mapRotation = 0;
    // gameState.map.mapPosition = [0, 0];
    // gameState.map.viewBox = [2000, 1716];
    // // Push non-map UI off-screen so it doesn't block clicks:
    // gameState.map.playerBoardsPosition = [-9999, -9999];
    // gameState.map.powerPlantMarketPosition = [-9999, -9999];
    // gameState.map.buttonsPosition = [-9999, -9999];
    // gameState.map.supplyPosition = [-9999, -9999];
    // gameState.map.roundInfoPosition = [-9999, -9999];
    // gameState.map.cityCountPosition = [-9999, -9999];
    // gameState.map.playerOrderPosition = [-9999, -9999];

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
