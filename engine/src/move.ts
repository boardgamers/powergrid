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
}

// Metadata attached to a move. Both stamps are ms-since-epoch and are stored in the
// log, so replaying a game reproduces the exact same times — the engine must never
// read the clock itself or replays would diverge. Engine-generated moves (AI, dropped
// players) omit them and simply don't tick the clocks.
//
// `time` is the ACTING CLIENT's wall clock when the move entered the turn buffer. It is
// the move's identity for reconciling the buffer against the server's echo (see the
// viewer's turn-buffer helpers), so it must survive untouched.
//
// `serverTime` is stamped once by the authoritative move processor (`wrapper.move`) from
// the SERVER clock. The per-player clocks are driven by it in preference to `time`:
// banking a clock stretch subtracts one player's stamp from another's, and browser
// clocks disagree (skew of a minute has been seen), so a client whose clock ran fast
// would otherwise charge that skew to itself on every turn — inflating its timer toward
// the whole game's elapsed time. A single server clock removes the skew.
export interface MoveMeta {
    time?: number;
    serverTime?: number;
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
}
