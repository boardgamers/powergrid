import { resolvePlayerColors } from '@/player-colors';
import { expect } from 'chai';

describe('custom and drafted player colours', () => {
    const defaults = ['limegreen', 'mediumorchid', 'red'];
    const players = [
        { id: 2, color: 'yellow' },
        { id: 0, color: 'dodgerblue' },
        { id: 1, color: 'brown' },
    ];

    it('keeps manual picks instead of replacing them with BGS generated defaults', () => {
        expect(
            resolvePlayerColors(defaults, players, {
                preferredPlayerColors: ['#13b7c8', null, null],
                bgs: { playerColors: ['#13b7c8', '#ba55d3', '#ff0000'] },
            })
        ).to.deep.equal(['#13b7c8', 'brown', 'yellow']);
        expect(resolvePlayerColors(defaults, players, { preferredPlayerColors: [null, null, null] })).to.deep.equal([
            'dodgerblue',
            'brown',
            'yellow',
        ]);
    });

    it('keeps the viewing player’s preference and resolves conflicting custom colours', () => {
        const preferences = { preferredPlayerColors: ['#13b7c8', '#14b8c9', null] };
        const own = resolvePlayerColors(defaults, players, preferences, 1);
        expect(own[1]).to.equal('#14b8c9');
        expect(own[0]).to.equal('dodgerblue');
        expect(own[2]).to.equal('yellow');
        expect(resolvePlayerColors(defaults, players, preferences)[0]).to.equal('#13b7c8');
    });

    it('moves only a conflicting game colour and preserves the other manual picks', () => {
        const colours = resolvePlayerColors(defaults, players, { preferredPlayerColors: ['#ffff00', null, null] });
        expect(colours).to.deep.equal(['#ffff00', 'brown', 'dodgerblue']);
        expect(new Set(colours).size).to.equal(3);
    });

    it('keeps readable game colours in colour-blind mode and ignores malformed preferences', () => {
        expect(
            resolvePlayerColors(defaults, players, { colorBlind: true, preferredPlayerColors: ['#123456'] })
        ).to.deep.equal(['dodgerblue', 'brown', 'yellow']);
        expect(
            resolvePlayerColors(defaults, players, { preferredPlayerColors: ['red', 'url(x)', null] })
        ).to.deep.equal(['dodgerblue', 'brown', 'yellow']);
    });

    it('does not let an older host’s complete palette overwrite manually drafted colours', () => {
        const preferences = { bgs: { playerColors: ['#123456', '#abcdef', '#654321'] } };
        expect(resolvePlayerColors(defaults, players, preferences)).to.deep.equal(['dodgerblue', 'brown', 'yellow']);
        expect(resolvePlayerColors(defaults, [], preferences)).to.deep.equal(preferences.bgs.playerColors);
    });
});
