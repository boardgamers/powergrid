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
    // Portrait phones stack the board into full-width rows. Per player, not per
    // game: it describes the screen you are holding, not the rules being played.
    stackOnPortrait: boolean;
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
    // Per-piece render scale override (House defaults to 0.035; Manhattan enlarges).
    scale?: number;
    side?: 'north' | 'south';
    // South Africa: this coal cube sits in the storage pool below the market.
    // Clicking emits buyResource with fromStorage:true (flat $8 buy).
    fromStorage?: boolean;
    // Empty spaces only: distance from the market's fill line, 1 for the space the
    // next cube would come back to. A purchase made this turn can be taken back by
    // clicking the ghost that holds it (#127), so the first `n` ranks are clickable
    // when the turn buffer holds `n` buys from that source.
    ghostRank?: number;
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
