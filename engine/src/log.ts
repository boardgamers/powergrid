import { Move } from './move';

export type LogEvent = {
    type: 'event';
    event: string;
    pretty?: string;
};

export type LogMove = {
    type: 'move';
    player: number;
    move: Move;
    simple: string;
    pretty: string;
};

export type LogItem = LogEvent | LogMove;
