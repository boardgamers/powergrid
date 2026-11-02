import BoardOption from '@/components/buttons/BoardOption.vue';
import PassButton from '@/components/buttons/PassButton.vue';
import UndoButton from '@/components/buttons/UndoButton.vue';
import Game from '@/components/Game.vue';
import { mount } from '@vue/test-utils';
import { expect } from 'chai';

describe('action label presentation', () => {
    it('switches phase labels without changing geometry, activation or disabled semantics', async () => {
        const wrapper = mount(PassButton, {
            propsData: {
                text: 'Finish buying',
                icon: 'resources',
                action: 'finish',
                enabled: true,
                width: 168,
                height: 32,
            },
        });
        const bounds = wrapper.find('.button-outline').attributes();
        await wrapper.setProps({ showText: true });
        expect(wrapper.find('[data-action-label]').text()).to.equal('Finish buying');
        expect(wrapper.find('[data-phase-icon]').exists()).to.equal(false);
        expect(wrapper.find('[data-action-icon]').exists()).to.equal(false);
        expect(wrapper.find('.button-divider').exists()).to.equal(false);
        expect(wrapper.find('.button-outline').attributes()).to.deep.equal(bounds);
        await wrapper.find('[data-action-label]').trigger('click');
        await wrapper.trigger('keydown.enter');
        await wrapper.trigger('keydown.space');
        expect(wrapper.emitted('click')!.length).to.equal(3);
        await wrapper.setProps({ enabled: false });
        await wrapper.trigger('click');
        await wrapper.trigger('keydown.enter');
        expect(wrapper.emitted('click')!.length).to.equal(3);
        expect(wrapper.attributes('aria-disabled')).to.equal('true');
        await wrapper.setProps({ showText: false });
        expect(wrapper.find('[data-action-label]').exists()).to.equal(false);
        expect(wrapper.find('[data-phase-icon]').exists()).to.equal(true);
        wrapper.destroy();
    });

    it('shows complete labels for local undo, saved-move undo and cancel bid edit', async () => {
        for (const [text, control, icon] of [
            ['Undo last move', 'undo', 'undo'],
            ['Undo my move', 'undo-move', 'undo'],
            ['Cancel bid edit', 'undo', 'cancel'],
        ]) {
            const wrapper = mount(UndoButton, {
                propsData: { text, control, icon, showText: true, width: 168, height: 32, enabled: true },
            });
            expect(wrapper.find('[data-action-label]').text()).to.equal(text);
            expect(wrapper.attributes('aria-label')).to.equal(text);
            expect(wrapper.find('image').exists()).to.equal(false);
            expect(wrapper.find('path').exists()).to.equal(false);
            await wrapper.trigger('keydown.space');
            expect(wrapper.emitted('click')!.length).to.equal(1);
            await wrapper.setProps({ enabled: false });
            await wrapper.trigger('click');
            expect(wrapper.emitted('click')!.length).to.equal(1);
            wrapper.destroy();
        }
    });

    it('toggles only the presentation preference, not game state or moves', () => {
        const events: any[] = [];
        const context = {
            preferences: { textActions: false },
            $set: (object: any, key: string, value: boolean) => {
                object[key] = value;
            },
            emitter: { emit: (...args: any[]) => events.push(args) },
        };
        const toggle = (Game as any).options.methods.toggleTextActions;
        toggle.call(context);
        expect(context.preferences.textActions).to.equal(true);
        toggle.call(context);
        expect(context.preferences.textActions).to.equal(false);
        expect(events).to.deep.equal([
            ['update:preference', { name: 'textActions', value: true }],
            ['update:preference', { name: 'textActions', value: false }],
        ]);
    });

    it('supports a keyboard toggle and exposes pressed state without making Rules a toggle', async () => {
        const wrapper = mount(BoardOption, {
            propsData: { control: 'text-actions', icon: 'text', label: 'Show action labels' },
        });
        expect(wrapper.attributes('aria-pressed')).to.equal('false');
        await wrapper.trigger('keydown.enter');
        await wrapper.trigger('keydown.space');
        expect(wrapper.emitted('click')!.length).to.equal(2);
        await wrapper.setProps({ active: true });
        expect(wrapper.attributes('aria-pressed')).to.equal('true');
        expect(wrapper.find('.active-marker').exists()).to.equal(true);
        await wrapper.setProps({ toggle: false, icon: 'rules', label: 'Rules' });
        expect(wrapper.attributes('aria-pressed')).to.equal(undefined);
        wrapper.destroy();
    });
});
