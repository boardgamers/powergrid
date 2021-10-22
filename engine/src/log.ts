import { Phase } from './gamestate';
import { Move } from './move';

export type LogPhase = {
    type: 'phase';
    phase: Phase;
};

export type LogEvent = {
    type: 'event';
    event: string;
};

export type LogMove = {
    type: 'move';
    player: number;
    move: Move;
    simple: string;
    pretty: string;
};

export type LogItem = LogPhase | LogEvent | LogMove;
