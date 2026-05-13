import { PowerPlant } from 'powergrid-engine/src/gamestate';

export interface UIData {
    waitingAnimations: number;
}

export type Preferences = {
    sound: boolean;
    disableHelp: boolean;
    adjustPlayerOrder: boolean;
    undoWholeTurn: boolean;
    fitToScreen: boolean;
};

export interface Piece {
    id: string;
    x: number;
    y: number;
    owner?: number;
    ownerName?: string;
    color?: string;
    powerPlant?: PowerPlant;
    transparent?: boolean;
    side?: 'north' | 'south';
    // South Africa: this coal cube sits in the storage pool below the market.
    // Clicking emits buyResource with fromStorage:true (flat $8 buy).
    fromStorage?: boolean;
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
