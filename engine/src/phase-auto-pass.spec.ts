import { expect } from 'chai';
import { cloneDeep } from 'lodash';
import * as wrapper from '../wrapper';
import { availableMoves } from './available-moves';
import { move as atomicMove, setup, stripSecret } from './engine';
import { GameOptions, GameState, Phase, ResourceType } from './gamestate';
import { LogMove } from './log';
import { Move, MoveName } from './move';
import { autoPassResourcesAndBuilding } from './phase-auto-pass';
import { automation } from './premoves';

const pass: Move = { name: MoveName.Pass, data: true };
function position(phase = Phase.Resources, map: GameOptions['map'] = 'Germany'): GameState {
    const G = setup(3, { map, variant: 'original', showMoney: false }, 'phase-auto-pass');
    G.phase = phase;
    G.round = 2;
    G.playerOrder = [0, 1, 2];
    G.currentPlayers = [2];
    G.newTurn = true;
    for (const p of G.players) {
        p.money = 0;
        p.passed = false;
        p.availableMoves = null;
    }
    G.players[2].availableMoves = availableMoves(G, G.players[2]);
    return G;
}
function passed(G: GameState): boolean {
    const start = G.log.length;
    const result = autoPassResourcesAndBuilding(G, 1234);
    return result.log.slice(start).some((e) => e.type === 'move' && e.player === 2 && e.move.name === MoveName.Pass);
}

describe('authoritative resource/building auto-pass', () => {
    for (const phase of [Phase.Resources, Phase.Building]) {
        const setting = phase === Phase.Resources ? 'autoPassResources' : 'autoPassBuilding';
        it(`${phase}: protects hidden affordability unless separately opted in`, () => {
            const G = position(phase);
            G.players[2].coalCapacity = 2;
            const before = cloneDeep(G);
            expect(passed(G)).to.equal(false);
            expect(G).to.deep.equal(before); // probe is read-only
            wrapper.setPlayerSettings(G, 2, {
                autoPassBids: true,
                [phase === Phase.Resources ? 'autoPassBuilding' : 'autoPassResources']: true,
            });
            expect(passed(G)).to.equal(false);
            wrapper.setPlayerSettings(G, 2, { [setting]: true });
            expect(passed(G)).to.equal(true);
            expect(wrapper.timeIncrements(G)).to.deep.equal([0, 0, 1]);
            expect(wrapper.isLiveUpdate(G)).to.equal(false);
            expect(G.players[2].money).to.equal(0);
        });
        it(`${phase}: public money auto-passes but affordable alternatives never do`, () => {
            const G = position(phase);
            G.options.showMoney = true;
            G.players[2].coalCapacity = 2;
            const affordable = cloneDeep(G);
            affordable.players[2].money = 100;
            wrapper.setPlayerSettings(affordable, 2, { [setting]: true });
            expect(passed(affordable)).to.equal(false);
            expect(passed(G)).to.equal(true);
        });
        it(`${phase}: refuses tentative, analysis and stripped states`, () => {
            for (const kind of ['tentative', 'analysis', 'stripped']) {
                const G = position(phase);
                G.options.showMoney = true;
                if (kind === 'tentative') G.newTurn = false;
                if (kind === 'analysis') G.achievementAnalysis = true;
                if (kind === 'stripped') G.players[2].money = -1;
                expect(passed(G)).to.equal(false);
            }
        });
    }
    it('passes full storage, no fuel plants and empty supply without consent', () => {
        expect(passed(position())).to.equal(true);
        const full = position();
        full.players[2].hybridCapacity = 4;
        full.players[2].coalLeft = 2;
        full.players[2].oilLeft = 2;
        expect(passed(full)).to.equal(true);
        const empty = position();
        empty.players[2].coalCapacity = 4;
        empty.coalMarket = 0;
        expect(passed(empty)).to.equal(true);
    });
    it('uses a rich Dijkstra probe and excludes impossible-city sentinels with either stall option', () => {
        for (const stallEnds of [true, false]) {
            const G = position(Phase.Building);
            G.options.stallEnds = stallEnds;
            G.players[2].cities = [{ name: G.map.cities[0].name, position: 1 }];
            expect(passed(G)).to.equal(false);
            G.blockedCities = G.map.cities.map((c) => c.name);
            expect(passed(G)).to.equal(true);
        }
    });
    it('retains legacy sentinel builds if actually affordable', () => {
        const G = position(Phase.Building);
        G.options.stallEnds = false;
        G.options.showMoney = true;
        G.blockedCities = G.map.cities.map((c) => c.name);
        G.players[2].money = 10000;
        expect(passed(G)).to.equal(false);
    });
    it('honors Japan round-one jump limits and the 21-house cap', () => {
        const G = position(Phase.Building, 'Japan');
        G.round = 1;
        G.players[2].cities = [{ name: G.map.startingCities![0], position: 1 }];
        expect(passed(G)).to.equal(false);
        G.players[2].usedFreeJump = true;
        expect(passed(G)).to.equal(true);
        const capped = position(Phase.Building);
        capped.players[2].cities = capped.map.cities.slice(0, 21).map((c) => ({ name: c.name, position: 1 }));
        expect(passed(capped)).to.equal(true);
    });
    it('retains free Wien garbage even with zero money and opt-in', () => {
        const G = position(Phase.Resources, 'Central Europe');
        G.options.wienFreeGarbage = true;
        G.players[2].cities = [{ name: 'Wien', position: 1 }];
        G.players[2].garbageCapacity = 2;
        G.garbageMarket = 24;
        wrapper.setPlayerSettings(G, 2, { autoPassResources: true });
        expect(availableMoves(G, G.players[2]).BuyResource).not.to.equal(undefined);
        expect(passed(G)).to.equal(false);
    });
    for (const map of ['USA', 'South Africa'] as const) {
        it(`recognizes ${map} off-track coal as a hidden affordability choice`, () => {
            const G = position(Phase.Resources, map);
            G.options.variant = 'recharged';
            G.players[2].coalCapacity = 2;
            G.coalMarket = 0;
            G.coalSupply = 2;
            if (map === 'South Africa') G.coalStorage = 2;
            expect(passed(G)).to.equal(false);
            G.coalSupply = 0;
            if (map === 'South Africa') G.coalStorage = 0;
            expect(passed(G)).to.equal(true);
        });
    }
    it('respects Korea side locks and Chile network market restrictions', () => {
        for (const map of ['Korea', 'Chile'] as const) {
            const G = position(Phase.Resources, map);
            G.players[2].coalCapacity = 2;
            G.coalMarket = 0;
            G.coalMarketNorth = 2;
            G.chosenSide = 'south';
            expect(passed(cloneDeep(G))).to.equal(true);
            G.chosenSide = 'north';
            expect(passed(G)).to.equal(false);
        }
    });
    it('does not auto-confirm an India resource purchase while it can be undone', async () => {
        const G = position(Phase.Resources, 'India');
        G.players[2].coalCapacity = 2;
        G.players[2].money = 50;
        G.players[2].availableMoves = availableMoves(G, G.players[2]);
        const buy = G.players[2].availableMoves!.BuyResource![0];
        const result = await wrapper.move(G, { name: MoveName.BuyResource, data: buy }, 2);
        expect(result.chosenResource).to.equal(ResourceType.Coal);
        expect(result.newTurn).to.equal(false);
        expect(wrapper.toSave(result)).to.equal(undefined);
        expect(wrapper.timeIncrements(result)).to.deep.equal([0, 0, 0]);
    });
    it('keeps last affordable purchases/builds tentative until explicit Done', async () => {
        for (const phase of [Phase.Resources, Phase.Building]) {
            const G = position(phase);
            G.options.showMoney = true;
            G.players[2].money = 10;
            G.players[2].coalCapacity = 1;
            G.players[2].availableMoves = availableMoves(G, G.players[2]);
            const input: Move =
                phase === Phase.Resources
                    ? { name: MoveName.BuyResource, data: G.players[2].availableMoves!.BuyResource![0] }
                    : { name: MoveName.Build, data: G.players[2].availableMoves!.Build![0] };
            const result = await wrapper.move(cloneDeep(G), input, 2);
            expect(result.newTurn).to.equal(false);
            expect(result.currentPlayers).to.deep.equal([2]);
            expect(wrapper.timeIncrements(result)).to.deep.equal([0, 0, 0]);
            const committed = await wrapper.move(cloneDeep(G), [input, pass], 2);
            expect(committed.newTurn).to.equal(true);
            expect(wrapper.timeIncrements(committed)[2]).to.be.greaterThan(0);
        }
    });
    it('interactive analysis never settles publicly impossible resource turns', async () => {
        const G = position();
        G.options.showMoney = true;
        const result = await wrapper.analysisMove(G, pass, 2);
        expect(result.phase).to.equal(Phase.Resources);
        expect(result.currentPlayers).to.deep.equal([1]);
        expect(result.players[1].passed).to.equal(false);
    });
    it('settings are strict, private, independent and never advance a turn', () => {
        const G = position();
        const before = cloneDeep(G);
        wrapper.setPlayerSettings(G, 2, { autoPassResources: true, autoPassBuilding: 'true' });
        expect(wrapper.playerSettings(G, 2)).to.deep.equal({
            autoPassBids: false,
            autoPassResources: true,
            autoPassBuilding: false,
        });
        expect(stripSecret(G, 1).players[2].settings).to.equal(undefined);
        expect(stripSecret(G).players[2].settings).to.equal(undefined);
        expect(stripSecret(G, 2).players[2].settings!.autoPassResources).to.equal(true);
        delete G.players[2].settings;
        expect(G).to.deep.equal(before);
    });
    it('settles resources into building and gives queued building/powering precedence', async () => {
        const G = position();
        G.options.showMoney = true;
        automation(G).plans[1] = {
            round: G.round,
            revision: 1,
            requestId: 'queued',
            phases: [
                { phase: Phase.Building, moves: [pass] },
                { phase: Phase.Bureaucracy, moves: [pass] },
            ],
        };
        const result = await wrapper.move(G, pass, 2);
        expect(result.phase).to.equal(Phase.Bureaucracy);
        expect(result.currentPlayers).not.to.include(1);
        expect(automation(result).plans[1].phases).to.have.length(0);
        expect(automation(result).plans[1].notice).to.equal('Your queued plants powered cities.');
        expect(wrapper.timeIncrements(result)).to.deep.equal([2, 3, 2]);
        expect(wrapper.isLiveUpdate(result)).to.equal(false);
        const passes = result.log.filter((e) => e.type === 'move');
        expect(passes).to.have.length(7);
        for (const entry of passes)
            if (entry.type === 'move') expect(entry.move.serverTime).to.equal((passes[0] as LogMove).move.serverTime);
    });
    it('replays ordinary auto-passes after settings change without re-running policy', async () => {
        let G = setup(3, { map: 'Germany', variant: 'original', showMoney: true }, 'auto-pass-replay-phases');
        for (let guard = 0; guard < 20 && G.phase === Phase.Auction; guard++) {
            const seat = G.currentPlayers[0];
            const legal = availableMoves(G, G.players[seat]);
            if (legal.ChoosePowerPlant?.length) {
                const choose: Move = { name: MoveName.ChoosePowerPlant, data: legal.ChoosePowerPlant[0] };
                const probe = atomicMove(cloneDeep(G), choose, seat);
                G = await wrapper.move(
                    G,
                    probe.newTurn === false ? [choose, { name: MoveName.Bid, data: 50 }] : choose,
                    seat
                );
            } else {
                G = await wrapper.move(G, pass, seat);
            }
        }
        for (let guard = 0; guard < 10 && G.phase !== Phase.Bureaucracy; guard++)
            G = await wrapper.move(G, pass, G.currentPlayers[0]);
        expect(G.phase).to.equal(Phase.Bureaucracy);
        expect(G.players.filter((p) => p.money === 0)).to.have.length(2);
        for (const p of G.players)
            wrapper.setPlayerSettings(G, p.id, { autoPassResources: true, autoPassBuilding: true });
        const replay = wrapper.replay(cloneDeep(G));
        expect(replay.phase).to.equal(G.phase);
        expect(replay.currentPlayers).to.deep.equal(G.currentPlayers);
        expect(replay.log).to.deep.equal(G.log);
        expect(JSON.parse(JSON.stringify(replay.players))).to.deep.equal(JSON.parse(JSON.stringify(G.players)));
        expect(wrapper.timeIncrements(replay)).to.deep.equal(wrapper.timeIncrements(G));
    });
    it('leaves mandatory auction choices and powering manual', () => {
        for (const phase of [Phase.Auction, Phase.Bureaucracy, Phase.ColorSelection, Phase.RegionSelection]) {
            expect(passed(position(phase))).to.equal(false);
        }
    });
});
