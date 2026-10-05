import { mount } from '@vue/test-utils';
import { expect } from 'chai';
import Game from '@/components/Game.vue';
import Calculator from '@/components/Calculator.vue';
import PassButton from '@/components/buttons/PassButton.vue';
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
    it('distinguishes resources, building and powering with icons and accessible labels without visible text', () => {
        const paths: string[] = [];
        for (const phase of [Phase.Resources, Phase.Building, Phase.Bureaucracy]) {
            const context = { G: { phase } };
            const text = computed('phaseButtonText', context);
            const icon = computed('phaseButtonIcon', context);
            const wrapper = mount(PassButton, { propsData: { text, icon, enabled: true } });
            expect(wrapper.attributes('aria-label')).to.equal(text);
            expect(wrapper.find('text').exists()).to.equal(false);
            paths.push(wrapper.find('path').attributes('d') as string);
            wrapper.destroy();
        }
        expect(new Set(paths).size).to.equal(3);
    });
});
