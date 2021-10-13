import { expect } from 'chai';
import { ended, setup } from './engine';

describe('Engine', () => {
    it('should setup a game correctly', () => {
        const G = setup(5, { fastBid: false }, 'test');

        // expect(G.factoriesLeft[0].id).to.equal('F1');
        // expect(G.factoriesLeft).to.have.length(20);
        // expect(G.players[0].factories[0].id).to.equal('F5');
        // expect(G.players[1].factories[0].id).to.equal('F15');
        // expect(G.players[2].factories[0].id).to.equal('F10');
        // expect(G.players[3].factories[0].id).to.equal('F20');
        // expect(G.players[4].factories[0].id).to.equal('F0');
    });

    it('should play full game', () => {
        const G = setup(5, { fastBid: false }, 'test');

        // G.currentPlayers = [0];
        // G.players[0].actions = 2;
        // G.players[0].availableMoves = availableMoves(G, G.players[0]);
        // G.players[0].factories[0] = ContainerColor.Brown;
        // G.players[1].factories[0] = ContainerColor.Orange;
        // G.players[2].factories[0] = ContainerColor.Black;
        // G.players[3].factories[0] = ContainerColor.Tan;
        // G.players[4].factories[0] = ContainerColor.White;
        // G.players[0].containersOnFactoryStore[0] = { containerColor: ContainerColor.Brown, price: 2 };
        // G.players[1].containersOnFactoryStore[0] = { containerColor: ContainerColor.Orange, price: 2 };
        // G.players[2].containersOnFactoryStore[0] = { containerColor: ContainerColor.Black, price: 2 };
        // G.players[3].containersOnFactoryStore[0] = { containerColor: ContainerColor.Tan, price: 2 };
        // G.players[4].containersOnFactoryStore[0] = { containerColor: ContainerColor.White, price: 2 };

        // G = execMove(G, { name: "buyFactory", data: ContainerColor.Orange } as Move, 0);
        // G = execMove(G, { name: "buyWarehouse", data: true } as Move, 0);
        // G = execMove(G, { name: "pass", data: true } as Move, 0);

        // G = execMove(G, { name: "buyFactory", data: ContainerColor.Tan } as Move, 1);
        // G = execMove(G, { name: "produce", data: ContainerColor.Orange, extraData: { price: 2 } } as Move, 1);
        // G = execMove(G, { name: "produce", data: ContainerColor.Tan, extraData: { price: 2 } } as Move, 1);
        // G = execMove(G, { name: "pass", data: true } as Move, 1);

        // G = execMove(G, { name: "buyWarehouse", data: true } as Move, 2);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 1, container: { containerColor: ContainerColor.Orange, price: 2 } }, extraData: { price: 4 } } as Move, 2);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 1, container: { containerColor: ContainerColor.Orange, price: 2 } }, extraData: { price: 4 } } as Move, 2);
        // G = execMove(G, { name: "pass", data: true } as Move, 2);

        // G = execMove(G, { name: "buyFactory", data: ContainerColor.Black } as Move, 3);
        // G = execMove(G, { name: "produce", data: ContainerColor.Black, extraData: { price: 3 } } as Move, 3);
        // G = execMove(G, { name: "produce", data: ContainerColor.Tan, extraData: { price: 2 } } as Move, 3);
        // G = execMove(G, { name: "pass", data: true } as Move, 3);

        // G = execMove(G, { name: "buyWarehouse", data: true } as Move, 4);
        // G = execMove(G, { name: "sail", data: ShipPosition.Player2 } as Move, 4);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 2, container: { containerColor: ContainerColor.Orange, price: 4 } } } as Move, 4);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 2, container: { containerColor: ContainerColor.Orange, price: 4 } } } as Move, 4);
        // G = execMove(G, { name: "pass", data: true } as Move, 4);

        // G = execMove(G, { name: "produce", data: ContainerColor.Orange, extraData: { price: 3 } } as Move, 0);
        // G = execMove(G, { name: "produce", data: ContainerColor.Brown, extraData: { price: 2 } } as Move, 0);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 2, container: { containerColor: ContainerColor.Black, price: 2 } }, extraData: { price: 3 } } as Move, 0);
        // G = execMove(G, { name: "pass", data: true } as Move, 0);

        // G = execMove(G, { name: "buyFactory", data: ContainerColor.White } as Move, 1);
        // G = execMove(G, { name: "produce", data: ContainerColor.Orange, extraData: { price: 2 } } as Move, 1);
        // G = execMove(G, { name: "produce", data: ContainerColor.Tan, extraData: { price: 2 } } as Move, 1);
        // G = execMove(G, { name: "produce", data: ContainerColor.White, extraData: { price: 3 } } as Move, 1);
        // G = execMove(G, { name: "pass", data: true } as Move, 1);

        // G = execMove(G, { name: "buyFactory", data: ContainerColor.Brown } as Move, 2);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 1, container: { containerColor: ContainerColor.Tan, price: 2 } }, extraData: { price: 3 } } as Move, 2);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 1, container: { containerColor: ContainerColor.Tan, price: 2 } }, extraData: { price: 3 } } as Move, 2);
        // G = execMove(G, { name: "pass", data: true } as Move, 2);

        // G = execMove(G, { name: "buyFactory", data: ContainerColor.Brown } as Move, 3);
        // G = execMove(G, { name: "produce", data: ContainerColor.Tan, extraData: { price: 2 } } as Move, 3);
        // G = execMove(G, { name: "produce", data: ContainerColor.Black, extraData: { price: 3 } } as Move, 3);
        // G = execMove(G, { name: "produce", data: ContainerColor.Brown, extraData: { price: 2 } } as Move, 3);
        // G = execMove(G, { name: "pass", data: true } as Move, 3);

        // G = execMove(G, { name: "buyWarehouse", data: true } as Move, 4);
        // G = execMove(G, { name: "sail", data: ShipPosition.OpenSea } as Move, 4);
        // G = execMove(G, { name: "pass", data: true } as Move, 4);

        // G = execMove(G, { name: "buyFromFactory", data: { player: 3, container: { containerColor: ContainerColor.Tan, price: 2 } }, extraData: { price: 4 } } as Move, 0);
        // G = execMove(G, { name: "sail", data: ShipPosition.Player2 } as Move, 0);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 2, container: { containerColor: ContainerColor.Tan, price: 3 } } } as Move, 0);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 2, container: { containerColor: ContainerColor.Tan, price: 3 } } } as Move, 0);
        // G = execMove(G, { name: "pass", data: true } as Move, 0);

        // G = execMove(G, { name: "produce", data: ContainerColor.Tan, extraData: { price: 3 } } as Move, 1);
        // G = execMove(G, { name: "produce", data: ContainerColor.Orange, extraData: { price: 3 } } as Move, 1);
        // G = execMove(G, { name: "produce", data: ContainerColor.White, extraData: { price: 3 } } as Move, 1);
        // G = execMove(G, { name: "arrangeFactory", data: { containerColor: ContainerColor.White, price: 3 }, extraData: { price: 2 } } as Move, 1);
        // G = execMove(G, { name: "arrangeFactory", data: { containerColor: ContainerColor.White, price: 3 }, extraData: { price: 2 } } as Move, 1);
        // G = execMove(G, { name: "arrangeFactory", data: { containerColor: ContainerColor.Orange, price: 3 }, extraData: { price: 2 } } as Move, 1);
        // G = execMove(G, { name: "arrangeFactory", data: { containerColor: ContainerColor.Tan, price: 3 }, extraData: { price: 2 } } as Move, 1);
        // G = execMove(G, { name: "sail", data: ShipPosition.Player0 } as Move, 1);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 0, container: { containerColor: ContainerColor.Black, price: 3 } } } as Move, 1);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 0, container: { containerColor: ContainerColor.Tan, price: 4 } } } as Move, 1);
        // G = execMove(G, { name: "pass", data: true } as Move, 1);

        // G = execMove(G, { name: "buyWarehouse", data: true } as Move, 2);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 1, container: { containerColor: ContainerColor.White, price: 2 } }, extraData: { price: 3 } } as Move, 2);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 1, container: { containerColor: ContainerColor.White, price: 2 } }, extraData: { price: 3 } } as Move, 2);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 1, container: { containerColor: ContainerColor.Orange, price: 2 } }, extraData: { price: 4 } } as Move, 2);
        // G = execMove(G, { name: "pass", data: true } as Move, 2);

        // G = execMove(G, { name: "buyWarehouse", data: true } as Move, 3);
        // G = execMove(G, { name: "produce", data: ContainerColor.Brown, extraData: { price: 1 } } as Move, 3);
        // G = execMove(G, { name: "arrangeFactory", data: { containerColor: ContainerColor.Brown, price: 2 }, extraData: { price: 1 } } as Move, 3);
        // G = execMove(G, { name: "arrangeFactory", data: { containerColor: ContainerColor.Black, price: 3 }, extraData: { price: 2 } } as Move, 3);
        // G = execMove(G, { name: "arrangeFactory", data: { containerColor: ContainerColor.Black, price: 3 }, extraData: { price: 2 } } as Move, 3);
        // G = execMove(G, { name: "pass", data: true } as Move, 3);

        // G = execMove(G, { name: "buyFromFactory", data: { player: 3, container: { containerColor: ContainerColor.Brown, price: 1 } }, extraData: { price: 4 } } as Move, 4);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 3, container: { containerColor: ContainerColor.Brown, price: 1 } }, extraData: { price: 4 } } as Move, 4);
        // G = execMove(G, { name: "sail", data: ShipPosition.Island } as Move, 4);
        // G = execMove(G, { name: "bid", data: true, extraData: { price: 1 } } as Move, 0);
        // G = execMove(G, { name: "bid", data: true, extraData: { price: 5 } } as Move, 1);
        // G = execMove(G, { name: "bid", data: true, extraData: { price: 4 } } as Move, 2);
        // G = execMove(G, { name: "bid", data: true, extraData: { price: 2 } } as Move, 3);
        // G = execMove(G, { name: "accept", data: 1 } as Move, 4);

        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 2, container: { containerColor: ContainerColor.White, price: 3 } } } as Move, 0);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 2, container: { containerColor: ContainerColor.White, price: 3 } } } as Move, 0);
        // G = execMove(G, { name: "sail", data: ShipPosition.OpenSea } as Move, 0);
        // G = execMove(G, { name: "pass", data: true } as Move, 0);

        // G = execMove(G, { name: "produce", data: ContainerColor.Orange, extraData: { price: 2 } } as Move, 1);
        // G = execMove(G, { name: "produce", data: ContainerColor.Tan, extraData: { price: 2 } } as Move, 1);
        // G = execMove(G, { name: "produce", data: ContainerColor.White, extraData: { price: 2 } } as Move, 1);
        // G = execMove(G, { name: "sail", data: ShipPosition.OpenSea } as Move, 1);
        // G = execMove(G, { name: "pass", data: true } as Move, 1);

        // G = execMove(G, { name: "sail", data: ShipPosition.Player4 } as Move, 2);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 4, container: { containerColor: ContainerColor.Brown, price: 4 } } } as Move, 2);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 4, container: { containerColor: ContainerColor.Brown, price: 4 } } } as Move, 2);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 3, container: { containerColor: ContainerColor.Black, price: 2 } }, extraData: { price: 3 } } as Move, 2);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 3, container: { containerColor: ContainerColor.Black, price: 2 } }, extraData: { price: 3 } } as Move, 2);
        // G = execMove(G, { name: "arrangeWarehouse", data: { containerColor: ContainerColor.Orange, price: 4 }, extraData: { price: 3 } } as Move, 2);
        // G = execMove(G, { name: "pass", data: true } as Move, 2);

        // G = execMove(G, { name: "sail", data: ShipPosition.Player2 } as Move, 3);
        // G = execMove(G, { name: "getLoan", data: true } as Move, 3);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 2, container: { containerColor: ContainerColor.Black, price: 3 } } } as Move, 3);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 2, container: { containerColor: ContainerColor.Black, price: 3 } } } as Move, 3);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 2, container: { containerColor: ContainerColor.Orange, price: 3 } } } as Move, 3);
        // G = execMove(G, { name: "sail", data: ShipPosition.OpenSea } as Move, 3);
        // G = execMove(G, { name: "pass", data: true } as Move, 3);

        // G = execMove(G, { name: "buyFromFactory", data: { player: 1, container: { containerColor: ContainerColor.White, price: 2 } }, extraData: { price: 4 } } as Move, 4);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 1, container: { containerColor: ContainerColor.Orange, price: 2 } }, extraData: { price: 3 } } as Move, 4);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 1, container: { containerColor: ContainerColor.Tan, price: 2 } }, extraData: { price: 3 } } as Move, 4);
        // G = execMove(G, { name: "sail", data: ShipPosition.OpenSea } as Move, 4);
        // G = execMove(G, { name: "pass", data: true } as Move, 4);

        // G = execMove(G, { name: "sail", data: ShipPosition.Island } as Move, 0);
        // G = execMove(G, { name: "getLoan", data: true } as Move, 1);
        // G = execMove(G, { name: "bid", data: true, extraData: { price: 11 } } as Move, 1);
        // G = execMove(G, { name: "getLoan", data: true } as Move, 2);
        // G = execMove(G, { name: "bid", data: true, extraData: { price: 8 } } as Move, 2);
        // G = execMove(G, { name: "bid", data: true, extraData: { price: 7 } } as Move, 3);
        // G = execMove(G, { name: "bid", data: true, extraData: { price: 9 } } as Move, 4);
        // G = execMove(G, { name: "accept", data: 1 } as Move, 0);

        // G = execMove(G, { name: "getLoan", data: true } as Move, 1);
        // G = execMove(G, { name: "sail", data: ShipPosition.Player4 } as Move, 1);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 4, container: { containerColor: ContainerColor.Tan, price: 3 } } } as Move, 1);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 4, container: { containerColor: ContainerColor.Orange, price: 3 } } } as Move, 1);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 4, container: { containerColor: ContainerColor.White, price: 4 } } } as Move, 1);
        // G = execMove(G, { name: "sail", data: ShipPosition.OpenSea } as Move, 1);
        // G = execMove(G, { name: "pass", data: true } as Move, 1);

        // G = execMove(G, { name: "payLoan", data: true } as Move, 2);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 0, container: { containerColor: ContainerColor.Brown, price: 2 } }, extraData: { price: 3 } } as Move, 2);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 0, container: { containerColor: ContainerColor.Brown, price: 2 } }, extraData: { price: 3 } } as Move, 2);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 3, container: { containerColor: ContainerColor.Tan, price: 2 } }, extraData: { price: 4 } } as Move, 2);
        // G = execMove(G, { name: "pass", data: true } as Move, 2);

        // G = execMove(G, { name: "sail", data: ShipPosition.Player2 } as Move, 3);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 2, container: { containerColor: ContainerColor.Brown, price: 3 } } } as Move, 3);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 2, container: { containerColor: ContainerColor.Tan, price: 4 } } } as Move, 3);
        // G = execMove(G, { name: "produce", data: ContainerColor.Brown, extraData: { price: 2 } } as Move, 3);
        // G = execMove(G, { name: "produce", data: ContainerColor.Black, extraData: { price: 3 } } as Move, 3);
        // G = execMove(G, { name: "produce", data: ContainerColor.Tan, extraData: { price: 2 } } as Move, 3);
        // G = execMove(G, { name: "pass", data: true } as Move, 3);

        // G = execMove(G, { name: "buyFromFactory", data: { player: 3, container: { containerColor: ContainerColor.Tan, price: 2 } }, extraData: { price: 4 } } as Move, 4);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 3, container: { containerColor: ContainerColor.Tan, price: 2 } }, extraData: { price: 4 } } as Move, 4);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 3, container: { containerColor: ContainerColor.Brown, price: 2 } }, extraData: { price: 2 } } as Move, 4);
        // G = execMove(G, { name: "sail", data: ShipPosition.Player2 } as Move, 4);
        // G = execMove(G, { name: "buyFromWarehouse", data: { player: 2, container: { containerColor: ContainerColor.Brown, price: 3 } } } as Move, 4);
        // G = execMove(G, { name: "pass", data: true } as Move, 4);

        // G = execMove(G, { name: "buyWarehouse", data: true } as Move, 0);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 1, container: { containerColor: ContainerColor.Tan, price: 2 } }, extraData: { price: 3 } } as Move, 0);
        // G = execMove(G, { name: "buyFromFactory", data: { player: 1, container: { containerColor: ContainerColor.Orange, price: 2 } }, extraData: { price: 4 } } as Move, 0);
        // G = execMove(G, { name: "pass", data: true } as Move, 0);

        // G = execMove(G, { name: "produce", data: ContainerColor.Orange, extraData: { price: 3 } } as Move, 1);
        // G = execMove(G, { name: "produce", data: ContainerColor.White, extraData: { price: 3 } } as Move, 1);
        // G = execMove(G, { name: "produce", data: ContainerColor.Tan, extraData: { price: 3 } } as Move, 1);
        // G = execMove(G, { name: "sail", data: ShipPosition.Island } as Move, 1);
        // G = execMove(G, { name: "bid", data: true, extraData: { price: 12 } } as Move, 2);
        // G = execMove(G, { name: "bid", data: true, extraData: { price: 5 } } as Move, 3);
        // G = execMove(G, { name: "bid", data: true, extraData: { price: 20 } } as Move, 4);
        // G = execMove(G, { name: "bid", data: true, extraData: { price: 7 } } as Move, 0);
        // G = execMove(G, { name: "accept", data: 4 } as Move, 1);

        // G = execMove(G, { name: "pass", data: true } as Move, 0);
        // G = execMove(G, { name: "pass", data: true } as Move, 1);
        // G = execMove(G, { name: "pass", data: true } as Move, 2);
        // G = execMove(G, { name: "pass", data: true } as Move, 3);
        // G = execMove(G, { name: "pass", data: true } as Move, 4);

        expect(ended(G)).to.be.false;
    });
});
