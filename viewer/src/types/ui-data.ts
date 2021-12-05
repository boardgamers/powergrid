import { PowerPlant } from 'powergrid-engine/src/gamestate';

export interface UIData {
    waitingAnimations: number;
}

export type Preferences = {
    sound: boolean;
    disableHelp: boolean;
    adjustPlayerOrder: boolean;
    undoWholeTurn: boolean;
};

export interface Piece {
    id: string;
    x: number;
    y: number;
    owner?: number;
    color?: string;
    powerPlant?: PowerPlant;
    isActualMarket?: boolean;
    transparent?: boolean;
}

export enum PieceType {
    House,
    Card,
    Coal,
    Oil,
    Garbage,
    Uranium,
    Hybrid,
}
