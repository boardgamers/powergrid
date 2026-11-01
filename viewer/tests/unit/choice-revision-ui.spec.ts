import PassButton from '@/components/buttons/PassButton.vue';
import Calculator from '@/components/Calculator.vue';
import Game from '@/components/Game.vue';
import { mount } from '@vue/test-utils';
import { expect } from 'chai';
import { Phase } from 'powergrid-engine';

const options = (Game as any).options;
const computed = (name: string, context: any) => options.computed[name].get.call(context);

describe('pending auction UI', () => {
    it('starts the reused calculator at the submitted bid and allows lowering it to the legal floor', async () => {
        const wrapper = mount(Calculator, { propsData: { minValue: 3, maxValue: 50, initialValue: 12 } });
        expect((wrapper.vm as any).value).to.equal(12);
        for (let i = 0; i < 20; i++) (wrapper.vm as any).sub();
        (wrapper.vm as any).bid();
        expect(wrapper.emitted('bid')![0]).to.deep.equal([3]);
        wrapper.destroy();
    });

    it('submits a replacement through the normal calculator without sending an ordinary turn', () => {
        const emitted: any[] = [];
        const context: any = {
            changingBid: true,
            editingBid: 'auction-1',
            revisableBid: 'auction-1',
            revisionBids: [3, 4, 5],
            emitter: { emit: (...args: any[]) => emitted.push(args) },
            sendMove: () => {
                throw new Error('revision must not use normal turn buffer');
            },
        };
        context.replaceBid = (pass: boolean) => options.methods.replaceBid.call(context, pass);
        options.methods.bid.call(context, 4);
        expect(emitted[0][1][0]).to.include({ name: 'Bid', data: 4, revision: 'auction-1' });
        expect(context.editingBid).to.equal(null);
    });

    it('does not send a stale edit after the auction changes', () => {
        const context = {
            editingBid: 'old-auction',
            revisableBid: 'new-auction',
            replacementBid: 4,
            revisionBids: [3, 4],
            emitter: {
                emit: () => {
                    throw new Error('stale revision');
                },
            },
        };
        expect(computed('changingBid', context)).to.equal(false);
        options.methods.replaceBid.call(context, false);
    });

    it('lets bidders replace their bid with a pass but never lets the auctioneer pass', () => {
        expect(computed('canUsePhaseButton', { changingBid: true, player: 1, G: { auctioningPlayer: 0 } })).to.equal(
            true
        );
        expect(computed('canUsePhaseButton', { changingBid: true, player: 0, G: { auctioningPlayer: 0 } })).to.equal(
            false
        );
    });
});

describe('phase button', () => {
    it('pairs distinct phase icons with skip or finish and complete accessible labels', () => {
        const paths: string[] = [];
        for (const phase of [Phase.Auction, Phase.Resources, Phase.Building, Phase.Bureaucracy]) {
            const context = {
                G: { phase },
                playerBoughtResourceThisTurn: () => true,
                playerBuiltCityThisTurn: () => true,
                playerActivatedPlantThisTurn: () => true,
            };
            const text = computed('phaseButtonText', context);
            const icon = computed('phaseButtonIcon', context);
            const action = computed('phaseButtonAction', context);
            expect(action).to.equal(phase === Phase.Auction ? 'skip' : 'finish');
            const wrapper = mount(PassButton, { propsData: { text, icon, action, enabled: true } });
            expect(wrapper.attributes('aria-label')).to.equal(text);
            expect(wrapper.find('text').exists()).to.equal(false);
            expect(wrapper.find('title').text()).to.equal(text);
            expect(wrapper.find('[data-action-icon]').attributes('d')).to.equal((wrapper.vm as any).actionPath);
            paths.push(wrapper.find('[data-phase-icon]').attributes('d') as string);
            wrapper.destroy();
        }
        expect(new Set(paths).size).to.equal(4);
    });

    it('highlights skip only when neither bidding nor choosing a plant is legal', () => {
        const context = (availableMoves: any) => ({
            canUsePhaseButton: true,
            phaseButtonAction: 'skip',
            player: 0,
            G: { players: [{ availableMoves }] },
        });
        expect(computed('highlightPhaseButton', context({ Pass: true }))).to.equal(true);
        expect(computed('highlightPhaseButton', context({ Pass: true, Bid: [11] }))).to.equal(false);
        expect(computed('highlightPhaseButton', context({ Pass: true, ChoosePowerPlant: [8] }))).to.equal(false);
        expect(computed('highlightPhaseButton', { ...context({}), canUsePhaseButton: false })).to.equal(false);
        expect(computed('highlightPhaseButton', { ...context({}), changingBid: true, revisionBids: [8] })).to.equal(
            false
        );
        expect(computed('highlightPhaseButton', { ...context({}), changingBid: true, revisionBids: [] })).to.equal(
            true
        );
    });

    it('shows skip until a resource is bought and restores skip after all buys are undone', () => {
        const context: any = { player: 0, G: { phase: Phase.Resources, log: [] } };
        context.playerBoughtResourceThisTurn = () => options.methods.playerBoughtResourceThisTurn.call(context);
        expect(computed('phaseButtonAction', context)).to.equal('skip');
        context.G.log.push({ type: 'move', player: 0, move: { name: 'BuyResource' } });
        expect(computed('phaseButtonAction', context)).to.equal('finish');
        context.G.log.pop();
        expect(computed('phaseButtonAction', context)).to.equal('skip');
        context.G.log.push({ type: 'move', player: 1, move: { name: 'BuyResource' } });
        expect(computed('phaseButtonAction', context)).to.equal('skip');
    });

    it('highlights resource skip only when buying is unavailable', () => {
        const context: any = {
            canUsePhaseButton: true,
            phaseButtonAction: 'skip',
            player: 0,
            G: {
                phase: Phase.Resources,
                players: [{ availableMoves: { Pass: true, BuyResource: [{ resource: 'coal' }] } }],
            },
        };
        expect(computed('highlightPhaseButton', context)).to.equal(false);
        context.G.players[0].availableMoves.BuyResource = [];
        expect(computed('highlightPhaseButton', context)).to.equal(true);
    });

    it('switches building from skip to finish and back when builds are undone', () => {
        const context: any = { player: 0, G: { phase: Phase.Building, log: [] } };
        context.playerBuiltCityThisTurn = () => options.methods.playerBuiltCityThisTurn.call(context);
        expect(computed('phaseButtonAction', context)).to.equal('skip');
        context.G.log.push({ type: 'move', player: 0, move: { name: 'Build' } });
        expect(computed('phaseButtonAction', context)).to.equal('finish');
        context.G.log.pop();
        expect(computed('phaseButtonAction', context)).to.equal('skip');
        context.G.log.push({ type: 'move', player: 1, move: { name: 'Build' } });
        expect(computed('phaseButtonAction', context)).to.equal('skip');
        context.G.log = [
            { type: 'move', player: 0, move: { name: 'Build' } },
            { type: 'move', player: 0, move: { name: 'Pass' } },
        ];
        expect(computed('phaseButtonAction', context)).to.equal('skip');
    });

    it('bases powering skip/finish on this player’s activated plants, including free plants', () => {
        const player = { powerPlants: [{ number: 3 }, { number: 13 }], powerPlantsNotUsed: [3, 13] };
        const context: any = { player: 0, G: { phase: Phase.Bureaucracy, players: [player] } };
        context.playerActivatedPlantThisTurn = () => options.methods.playerActivatedPlantThisTurn.call(context);
        expect(computed('phaseButtonAction', context)).to.equal('skip');
        player.powerPlantsNotUsed = [3];
        expect(computed('phaseButtonAction', context)).to.equal('finish');
        player.powerPlantsNotUsed = [3, 13];
        expect(computed('phaseButtonAction', context)).to.equal('skip');
        context.canChangePowering = true;
        expect(computed('phaseButtonAction', context)).to.equal('edit');
    });

    it('keeps building/powering skip black while choices exist, blue otherwise', () => {
        for (const [phase, move] of [
            [Phase.Building, 'Build'],
            [Phase.Bureaucracy, 'UsePowerPlant'],
        ]) {
            const context: any = {
                canUsePhaseButton: true,
                phaseButtonAction: 'skip',
                player: 0,
                G: { phase, players: [{ availableMoves: { [move]: [{}] } }] },
            };
            expect(computed('highlightPhaseButton', context)).to.equal(false);
            context.G.players[0].availableMoves[move] = [];
            expect(computed('highlightPhaseButton', context)).to.equal(true);
            context.phaseButtonAction = 'finish';
            expect(computed('highlightPhaseButton', context)).to.equal(true);
        }
    });

    it('keeps skip styling while accepting the only-option highlight', async () => {
        const wrapper = mount(PassButton, {
            propsData: { text: 'Pass bid', action: 'skip', enabled: true, highlightButton: false },
        });
        expect(wrapper.classes()).to.include('skip-action');
        expect(wrapper.classes()).not.to.include('highlightButton');
        await wrapper.setProps({ highlightButton: true });
        expect(wrapper.classes()).to.include('highlightButton');
        wrapper.destroy();
    });

    it('uses equal-scale icons and paints one shared outline above both backgrounds', () => {
        const wrapper = mount(PassButton, { propsData: { text: 'Pass bid', icon: 'auction', action: 'skip' } });
        expect(wrapper.find('[data-phase-icon]').attributes('transform')).to.equal('translate(12, 5)');
        expect(wrapper.find('[data-action-icon]').attributes('transform')).to.equal('translate(52, 5)');
        const children = Array.from(wrapper.element.children);
        const outline = wrapper.find('.button-outline');
        expect(children.indexOf(outline.element)).to.be.greaterThan(
            children.indexOf(wrapper.find('[data-action-icon]').element)
        );
        expect(outline.attributes('fill')).to.equal('none');
        expect(outline.attributes('pointer-events')).to.equal('none');
        wrapper.destroy();
    });

    it('keeps the phase visible when editing and uses skip when passing a revised bid', () => {
        for (const context of [
            { G: { phase: Phase.Auction }, revisableBid: 'bid' },
            { G: { phase: Phase.Bureaucracy }, canChangePowering: true },
        ]) {
            expect(computed('phaseButtonAction', context)).to.equal('edit');
            expect(computed('phaseButtonIcon', context)).to.equal(
                context.G.phase === Phase.Auction ? 'auction' : 'powering'
            );
        }
        expect(computed('phaseButtonAction', { changingBid: true, revisableBid: 'bid' })).to.equal('skip');
    });

    it('makes either pictogram part of the same enabled action, including keyboard activation', async () => {
        const wrapper = mount(PassButton, {
            propsData: { text: 'Pass bid', icon: 'auction', action: 'skip', enabled: true },
        });
        await wrapper.find('[data-phase-icon]').trigger('click');
        await wrapper.find('[data-action-icon]').trigger('click');
        await wrapper.trigger('keydown.enter');
        await wrapper.trigger('keydown.space');
        expect(wrapper.emitted('click')!.length).to.equal(4);
        await wrapper.setProps({ enabled: false });
        await wrapper.find('[data-action-icon]').trigger('click');
        await wrapper.trigger('keydown.enter');
        expect(wrapper.emitted('click')!.length).to.equal(4);
        wrapper.destroy();
    });
});
