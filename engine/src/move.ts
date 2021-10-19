import { ResourceType } from './gamestate';

export declare namespace Moves {
    export interface MoveChoosePowerPlant {
        name: MoveName.ChoosePowerPlant;
        data: number;
    }

    export interface MoveBid {
        name: MoveName.Bid;
        data: number;
    }

    export interface MoveDiscardPowerPlant {
        name: MoveName.DiscardPowerPlant;
        data: number;
    }

    export interface MoveDiscardResources {
        name: MoveName.DiscardResources;
        data: ResourceType;
    }

    export interface MoveBuyResource {
        name: MoveName.BuyResource;
        data: {
            resource: ResourceType;
        };
    }

    export interface MoveBuild {
        name: MoveName.Build;
        data: {
            name: string;
            price: number;
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

    export interface MovePass {
        name: MoveName.Pass;
        data: true;
    }

    export interface MoveUndo {
        name: MoveName.Undo;
        data: true;
    }
}

export type Move =
    | Moves.MoveChoosePowerPlant
    | Moves.MoveBid
    | Moves.MoveDiscardPowerPlant
    | Moves.MoveDiscardResources
    | Moves.MoveBuyResource
    | Moves.MoveBuild
    | Moves.MoveUsePowerPlant
    | Moves.MovePass
    | Moves.MoveUndo;

export enum MoveName {
    ChoosePowerPlant = 'ChoosePowerPlant',
    Bid = 'Bid',
    DiscardPowerPlant = 'DiscardPowerPlant',
    DiscardResources = 'DiscardResources',
    BuyResource = 'BuyResource',
    Build = 'Build',
    UsePowerPlant = 'UsePowerPlant',
    Pass = 'Pass',
    Undo = 'Undo',
}
