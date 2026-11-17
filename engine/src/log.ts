import { Move } from './move';

export type LogEvent = {
    type: 'event';
    /** Analysis-only state edit; intentionally not a gameplay move. */
    analysisMoney?: import('./analysis-money').SetAnalysisMoney['data'];
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
