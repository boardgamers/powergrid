import { expect } from 'chai';
import { init, replay, toSave } from '../wrapper';
import { move, reconstructState, setup } from './engine';
import { Phase, playerColors } from './gamestate';
import { MoveName } from './move';

describe('custom colours at setup', () => {
    it('skips exactly the custom-colour seats for every mixture of two to six players', async () => {
        for (let count = 2; count <= 6; count++) {
            for (let mask = 0; mask < 2 ** count; mask++) {
                const preferred = Array.from({ length: count }, (_, i) => (mask & (1 << i) ? '#13b7c8' : null));
                let state = await init(count, [], { map: 'Germany', chooseColors: true }, 'colour-mix', undefined, {
                    preferredPlayerColors: preferred,
                });
                const picks: number[] = [];
                while (state.phase === Phase.ColorSelection) {
                    const seat = state.currentPlayers[0];
                    expect(preferred[seat]).to.equal(null);
                    const options = state.players[seat].availableMoves!.ChooseColor!;
                    expect(options.length).to.equal(6 - picks.length);
                    picks.push(seat);
                    state = move(state, { name: MoveName.ChooseColor, data: options[options.length - 1] }, seat);
                    expect(toSave(state)).to.exist;
                }
                expect(picks).to.deep.equal(state.playerOrder.filter((i) => !preferred[i]));
                expect(state.phase).to.equal(Phase.Auction);
                expect(new Set(state.players.map((p) => p.color)).size).to.equal(count);
                expect(state.players.every((p) => playerColors.includes(p.color!))).to.equal(true);
                expect(state.currentPlayers).to.deep.equal([state.playerOrder[0]]);
                expect(state.players[state.currentPlayers[0]].availableMoves!.ChoosePowerPlant).to.exist;
                expect(toSave(state)).to.exist;
                for (const restored of [replay(state), reconstructState(state)]) {
                    expect(restored.players.map((p) => p.color)).to.deep.equal(state.players.map((p) => p.color));
                    expect(restored.setupPlayerColors).to.deep.equal(state.setupPlayerColors);
                    expect(restored.phase).to.equal(state.phase);
                }
            }
        }
    });

    it('hands all-custom tables straight to region selection and snapshots preferences by value', () => {
        const preferred = ['#abcdef', '#123456', '#abcdef'];
        const state = setup(
            3,
            { map: 'Germany', chooseColors: true, chooseRegions: true },
            'colour-regions',
            undefined,
            undefined,
            preferred
        );
        preferred[0] = '#987654';
        expect(state.setupPlayerColors![0]).to.equal('#abcdef');
        expect(state.phase).to.equal(Phase.RegionSelection);
        expect(state.players[state.currentPlayers[0]].availableMoves!.ChooseRegion).to.exist;
        expect(replay(state, { to: 0 }).phase).to.equal(Phase.RegionSelection);
    });

    it('does not change games with colour selection off or with invalid custom colours', () => {
        const normal = setup(3, { map: 'Germany' }, 'colour-off');
        const custom = setup(3, { map: 'Germany' }, 'colour-off', undefined, undefined, ['#abcdef']);
        expect(custom).to.deep.equal(normal);
        const invalid = setup(3, { map: 'Germany', chooseColors: true }, 'colour-invalid', undefined, undefined, [
            'red',
            'url(x)',
            null,
        ]);
        expect(invalid.setupPlayerColors).to.equal(undefined);
        expect(invalid.phase).to.equal(Phase.ColorSelection);
        expect(invalid.currentPlayers).to.deep.equal([0]);
    });
});
