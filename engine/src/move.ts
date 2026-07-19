import { ResourceType } from './gamestate';

export declare namespace Moves {
    export interface MoveChoosePowerPlant {
        name: MoveName.ChoosePowerPlant;
        data: number;
        usedPlantDiscount?: boolean;
    }

    export interface MoveBid {
        name: MoveName.Bid;
        data: number;
    }

    export interface MoveDiscardPowerPlant {
        name: MoveName.DiscardPowerPlant;
        data: number;
        extra?: number[];
    }

    export interface MoveDiscardResources {
        name: MoveName.DiscardResources;
        data: ResourceType;
    }

    export interface MoveBuyResource {
        name: MoveName.BuyResource;
        data: {
            resource: ResourceType;
            // Korea: which side's market the resource was bought from.
            // Omitted on all other maps.
            side?: 'north' | 'south';
            // South Africa: coal bought from the storage pool below the market
            // ($8 flat) rather than from the market. Omitted on all other maps
            // and on regular SA market buys.
            fromStorage?: boolean;
        };
        fromSupply?: boolean;
    }

    export interface MoveBuild {
        name: MoveName.Build;
        data: {
            name: string;
            price: number;
            freeJump?: boolean;
        };
    }

    export interface MoveUsePowerPlant {
        name: MoveName.UsePowerPlant;
        data: {
            powerPlant: number;
            resourcesSpent: ResourceType[];
            citiesPowered: number;
        };
    }

    export interface MoveChooseRegion {
        name: MoveName.ChooseRegion;
        data: string;
    }

    export interface MoveChooseColor {
        name: MoveName.ChooseColor;
        data: string;
    }

    export interface MovePass {
        name: MoveName.Pass;
        data: true;
    }

    export interface MoveUndo {
        name: MoveName.Undo;
        data: boolean;
    }
}

// Metadata the client may attach to any move. `time` is the wall-clock timestamp
// (ms since epoch) at which the move was submitted; it drives the per-player
// clocks. It is stored in the log, so replaying a game reproduces the exact same
// times — the engine must never read the clock itself or replays would diverge.
// Engine-generated moves (AI, dropped players) omit it and simply don't tick the
// clocks.
export interface MoveMeta {
    time?: number;
}

export type Move = (
    | Moves.MoveChoosePowerPlant
    | Moves.MoveBid
    | Moves.MoveDiscardPowerPlant
    | Moves.MoveDiscardResources
    | Moves.MoveBuyResource
    | Moves.MoveBuild
    | Moves.MoveUsePowerPlant
    | Moves.MoveChooseRegion
    | Moves.MoveChooseColor
    | Moves.MovePass
    | Moves.MoveUndo
) &
    MoveMeta;

export enum MoveName {
    ChoosePowerPlant = 'ChoosePowerPlant',
    Bid = 'Bid',
    DiscardPowerPlant = 'DiscardPowerPlant',
    DiscardResources = 'DiscardResources',
    BuyResource = 'BuyResource',
    Build = 'Build',
    UsePowerPlant = 'UsePowerPlant',
    ChooseRegion = 'ChooseRegion',
    ChooseColor = 'ChooseColor',
    Pass = 'Pass',
    Undo = 'Undo',
}
