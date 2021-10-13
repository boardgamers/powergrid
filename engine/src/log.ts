import { Phase } from './gamestate';
import { Move } from './move';

export enum GameEventName {
    GameStart = 'Game Start!',
    GameEnd = 'Game End!',
    Upkeep = 'Upkeep',
}

export declare namespace GameEvents {
    export interface GameStart {
        name: GameEventName.GameStart;
    }

    export interface GameEnd {
        name: GameEventName.GameEnd;
    }

    export interface Upkeep {
        name: GameEventName.Upkeep;
        interest: string;
    }
}

type GameEvent = GameEvents.GameStart | GameEvents.GameEnd | GameEvents.Upkeep;

export type LogPhase = {
    type: 'phase';
    phase: Phase;
};

export type LogEvent = {
    type: 'event';
    event: GameEvent;
};

export type LogMove = {
    type: 'move';
    player: number;
    move: Move;
    simple: string;
    pretty: string;
};

export type LogItem = LogPhase | LogEvent | LogMove;
