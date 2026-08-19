import { cloneDeep } from 'lodash';
import { move as execMove, Move, Phase, setup, stripSecret } from 'powergrid-engine';
import { moveAI } from 'powergrid-engine/src/engine';
import type { MapName, Variant } from 'powergrid-engine/src/gamestate';
import launch from './launch';

const delayBase = 0;

function launchSelfContained(selector = '#app') {
    const strip = true;

    const emitter = launch(selector);

    // The sandbox game can be steered from the URL so a layout or rules change can
    // be checked against several maps without editing this file each time, e.g.
    //   ?map=Australia&players=3&variant=original&seed=7
    const params = new URLSearchParams(window.location.search);
    // Note: randomizeMap short-circuits region selection in setup(), so ticking
    // both gives a randomized board with no draft. They are alternatives.
    const gameOptions = {
        map: (params.get('map') || 'Bremen') as MapName,
        variant: (params.get('variant') || 'recharged') as Variant,
        showMoney: true,
        randomizeMap: params.get('randomize') === '1',
        chooseRegions: params.get('regions') === '1',
    };
    let gameState = setup(Number(params.get('players')) || 6, gameOptions, params.get('seed') || '0');

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

    emitter.on('move', async (moves: Move | Move[]) => {
        setTimeout(() => {
            console.log('moves received', moves);

            // Mimic the platform: replay the whole turn buffer from the last committed
            // state; only keep (persist) the result once the turn is committed.
            let newState = cloneDeep(gameState);
            for (const move of Array.isArray(moves) ? moves : [moves]) {
                newState = execMove(newState, move, playerIndex);
            }
            console.log('new game state', newState);

            if (newState.newTurn === false) {
                // Tentative: just echo the state back to the acting player
                emitter.emit('state', cloneDeep(strip ? stripSecret(newState, playerIndex) : newState));
                return;
            }

            gameState = newState;
            emitter.emit('state', cloneDeep(strip ? stripSecret(gameState, playerIndex) : gameState));

            let delay = delayBase;
            const moveAIAux = () => {
                if (gameState.players.some((pl) => pl.isAI && pl.availableMoves)) {
                    gameState = moveAI(
                        gameState,
                        gameState.players.findIndex((pl) => pl.isAI && pl.availableMoves)
                    );
                    // Only broadcast committed states: the human viewer discards
                    // tentative states that don't match its own turn buffer.
                    if (gameState.newTurn !== false) {
                        let newAIState = cloneDeep(strip ? stripSecret(gameState, playerIndex) : gameState);
                        console.log('new game state', newAIState);
                        emitter.emit('state', newAIState);
                    }
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
        // Only broadcast committed states (see moveAIAux above).
        if (gameState.newTurn !== false) {
            let newState = cloneDeep(strip ? stripSecret(gameState, playerIndex) : gameState);
            setTimeout(() => emitter.emit('state', newState), delay);
            delay += delayBase;
        }
    }

    console.log('available moves', gameState.players[playerIndex].availableMoves);
}

export default launchSelfContained;
