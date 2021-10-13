import { ContainerPiece, ShipPosition } from 'container-engine/src/gamestate';
import PieceComponent from '../components/pieces/Piece.vue';

export interface UIData {
    dragged?: PieceComponent | null;
    waitingAnimations: number;
}

export type Preferences = {
    sound: boolean;
    disableHelp: boolean;
};

export interface Piece {
    id: string;
    x: number;
    y: number;
    owner?: number;
    color?: string;
    rotate?: number;
    state?: string;
}

export interface ShipType extends Piece {
    containers: ContainerPiece[];
    position: ShipPosition;
}

export enum PieceType {
    Warehouse = 'warehouse',
    Factory = 'factory',
    Container = 'container',
    Ship = 'ship',
    Loan = 'loan',
}

export enum DropZoneType {
    Ship = 'ship',
    PlayerHarbor11 = 'playerHarbor11',
    PlayerHarbor12 = 'playerHarbor12',
    PlayerHarbor13 = 'playerHarbor13',
    PlayerHarbor14 = 'playerHarbor14',
    PlayerHarbor21 = 'playerHarbor21',
    PlayerHarbor22 = 'playerHarbor22',
    PlayerHarbor23 = 'playerHarbor23',
    PlayerHarbor24 = 'playerHarbor24',
    PlayerHarbor31 = 'playerHarbor31',
    PlayerHarbor32 = 'playerHarbor32',
    PlayerHarbor33 = 'playerHarbor33',
    PlayerHarbor34 = 'playerHarbor34',
    PlayerHarbor41 = 'playerHarbor41',
    PlayerHarbor42 = 'playerHarbor42',
    PlayerHarbor43 = 'playerHarbor43',
    PlayerHarbor44 = 'playerHarbor44',
    Factory = 'factory',
    FactoryStore = 'factoryStore',
    Warehouse = 'warehouse',
    WarehouseStore = 'warehouseStore',
    OpenSea = 'openSea',
    IslandHarbor = 'islandHarbor',
    GetLoan = 'getLoan',
    PayLoan = 'payLoan',
    Supply = 'supply',
}

export enum ContainerState {
    OnBoard = 'onBoard',
    OnFactoryStore = 'onFactoryStore',
    OnWarehouseStore = 'onWarehouseStore',
    OnShip = 'onShip',
    OnIsland = 'onIsland',
}
