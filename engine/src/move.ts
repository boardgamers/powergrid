import { ResourceType } from './gamestate';

export declare namespace Moves {
    export interface MoveChoosePowerPlant {
        name: MoveName.ChoosePowerPlant;
        data: {
            powerPlant: number;
            startingPrice: number;
        };
    }

    export interface MoveBid {
        name: MoveName.Bid;
        data: {
            price: number;
        };
    }

    export interface MoveDiscardPowerPlant {
        name: MoveName.DiscardPowerPlant;
        data: {
            powerPlant: number;
        };
    }

    export interface MoveDiscardResources {
        name: MoveName.DiscardResources;
        data: {
            resourcesDiscarded: ResourceType[];
        };
    }

    export interface MoveBuyResource {
        name: MoveName.BuyResource;
        data: {
            resource: ResourceType;
            price: number;
        };
    }

    export interface MoveBuild {
        name: MoveName.Build;
        data: {
            city: string;
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
    ChoosePowerPlant,
    Bid,
    DiscardPowerPlant,
    DiscardResources,
    BuyResource,
    Build,
    UsePowerPlant,
    Pass,
    Undo
}
