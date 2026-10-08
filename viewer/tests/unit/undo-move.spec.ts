import UndoButton from '@/components/buttons/UndoButton.vue';
import Game from '@/components/Game.vue';
import { takesBackOwnMoves } from '@/util/turn-buffer';
import { mount } from '@vue/test-utils';
import { expect } from 'chai';
import type { GameState, LogItem } from 'powergrid-engine';
import { MoveName } from 'powergrid-engine';

const options = (Game as any).options;
const canUndoMove = (context: any) => options.methods.canUndoMove.call(context);

const move = (player: number, name: MoveName, data: unknown, time: number): LogItem => ({
    type: 'move',
    player,
    move: { name, data, time } as any,
    simple: '',
    pretty: '',
});
const withLog = (log: LogItem[]) => ({ log } as GameState);

describe('Undo my move', () => {
    const start: LogItem[] = [{ type: 'event', event: 'Game Start!' }];
    const mine = move(0, MoveName.ChoosePowerPlant, 3, 1);
    const bot = move(1, MoveName.Bid, 4, 2);
    const mineAgain = move(0, MoveName.Bid, 5, 3);

    it('recognizes a committed state that takes back the player’s own moves', () => {
        const before = [...start, mine, bot, mineAgain];
        expect(takesBackOwnMoves(before, withLog([...start, mine, bot]), 0)).to.equal(true);
        expect(takesBackOwnMoves(before, withLog(start), 0)).to.equal(true);
        expect(takesBackOwnMoves(before, withLog([...before, move(1, MoveName.Pass, true, 4)]), 0)).to.equal(false);
        // Another player's revision only removes their own moves.
        expect(takesBackOwnMoves(before, withLog([...start, mine, mineAgain]), 0)).to.equal(false);
        expect(takesBackOwnMoves(before, withLog([...start, mine, bot]), 1)).to.equal(false);
        expect(takesBackOwnMoves(null, withLog(start), 0)).to.equal(false);
        expect(takesBackOwnMoves(before, withLog(start), undefined)).to.equal(false);
    });

    const offered = () => ({
        undoAvailable: true,
        G: { players: [{}, {}] },
        player: 0,
        paused: false,
        interactionDisabled: false,
        tutorialMove: undefined,
        preferences: {},
        roundPlan: null,
        pendingPlanId: '',
        changingBid: false,
        poweringSubmitting: false,
        undoRequested: false,
        recentLocalUndo: false,
        canUndo: () => false,
    });

    it('is offered only while BGS allows it and the player can act on the live board', () => {
        expect(canUndoMove(offered())).to.equal(true);
        expect(canUndoMove({ ...offered(), undoAvailable: false }), 'hidden by default').to.equal(false);
        expect(canUndoMove({ ...offered(), player: undefined }), 'spectators').to.equal(false);
        expect(canUndoMove({ ...offered(), G: null }), 'no state yet').to.equal(false);
        expect(canUndoMove({ ...offered(), paused: true }), 'replaying').to.equal(false);
        expect(canUndoMove({ ...offered(), preferences: { analysis: true } }), 'analyses').to.equal(false);
        expect(canUndoMove({ ...offered(), interactionDisabled: true })).to.equal(false);
        expect(canUndoMove({ ...offered(), tutorialMove: () => undefined }), 'tutorials').to.equal(false);
        expect(canUndoMove({ ...offered(), roundPlan: { entries: [] } }), 'round planning').to.equal(false);
        expect(canUndoMove({ ...offered(), pendingPlanId: 'request' }), 'premoves on their way').to.equal(false);
        expect(canUndoMove({ ...offered(), poweringSubmitting: true }), 'powering on its way').to.equal(false);
        expect(canUndoMove({ ...offered(), undoRequested: true }), 'undo on its way').to.equal(false);
        expect(canUndoMove({ ...offered(), changingBid: true }), 'bid edit in progress').to.equal(false);
        expect(canUndoMove({ ...offered(), canUndo: () => true }), 'buffered moves come first').to.equal(false);
        expect(canUndoMove({ ...offered(), recentLocalUndo: true }), 'just after the local Undo').to.equal(false);
    });

    it('asks BGS once per request', () => {
        const emitted: unknown[][] = [];
        const context: any = { ...offered(), emitter: { emit: (...args: unknown[]) => emitted.push(args) } };
        context.canUndoMove = () => canUndoMove(context);
        options.methods.undoMove.call(context);
        // A second click before BGS answers with the earlier state.
        options.methods.undoMove.call(context);
        clearTimeout(context.undoRequestTimer);
        expect(emitted).to.deep.equal([['undo']]);
        expect(context.undoRequested).to.equal(true);
    });

    it('drops drafts made on the newer position', () => {
        const context: any = {
            turnMoves: [{ name: MoveName.BuyResource }],
            editingBid: 'auction',
            confirmVisible: true,
            discardVisible: true,
            freeJumpVisible: true,
            discardedPowerPlant: {},
            freeJumpCity: {},
            soleBuyerPlant: {},
            draftKey: 2,
            roundPlan: null,
            G: {},
        };
        options.methods.abandonLocalTurn.call(context);
        expect(context).to.deep.include({
            turnMoves: [],
            editingBid: null,
            confirmVisible: false,
            discardVisible: false,
            freeJumpVisible: false,
            discardedPowerPlant: null,
            freeJumpCity: null,
            soleBuyerPlant: null,
            draftKey: 3,
            G: null,
        });
        const planning: any = { ...context, roundPlan: { entries: [] }, G: { plan: true } };
        options.methods.abandonLocalTurn.call(planning);
        expect(planning.G).to.deep.equal({ plan: true });
    });

    it('keeps a double click on the board’s Undo away from the saved move', () => {
        let undone = 0;
        const context: any = { changingBid: false, editingBid: null, undo: () => undone++ };
        options.methods.useUndoButton.call(context);
        clearTimeout(context.recentLocalUndoTimer);
        expect(undone).to.equal(1);
        expect(context.recentLocalUndo).to.equal(true);
        const editing: any = { changingBid: true, editingBid: 'auction', undo: () => undone++ };
        options.methods.useUndoButton.call(editing);
        clearTimeout(editing.recentLocalUndoTimer);
        expect(editing.editingBid).to.equal(null);
        expect(undone).to.equal(1);
    });

    it('renders an accessible board control with the undo icon', async () => {
        const wrapper = mount(UndoButton, {
            propsData: { control: 'undo-move', text: 'Undo my move', enabled: true, highlightButton: true },
        });
        expect(wrapper.attributes('data-board-control')).to.equal('undo-move');
        expect(wrapper.attributes('aria-label')).to.equal('Undo my move');
        expect(wrapper.find('title').text()).to.equal('Undo my move');
        expect(wrapper.find('image').exists()).to.equal(true);
        await wrapper.trigger('click');
        await wrapper.trigger('keydown.enter');
        expect(wrapper.emitted('click')).to.have.length(2);
        await wrapper.setProps({ control: 'undo', text: 'Cancel bid edit', icon: 'cancel' });
        expect(wrapper.attributes('data-board-control')).to.equal('undo');
        expect(wrapper.find('image').exists()).to.equal(false);
        expect(wrapper.find('path').exists()).to.equal(true);
        wrapper.destroy();
    });
});
