import PowerPlantMarket from '@/components/boards/PowerPlantMarket.vue';
import { shallowMount } from '@vue/test-utils';
import { expect } from 'chai';

describe('market choice highlights', () => {
    it('groups the market while muting unavailable choices and follows eligibility changes', async () => {
        const wrapper = shallowMount(PowerPlantMarket, {
            propsData: { canChoose: true, chooseablePowerPlants: [8, 10] },
            provide: { preferences: {} },
        });
        await wrapper.setData({
            actualMarketCards: [
                { id: 'a', x: 165, y: 24, powerPlant: { number: 8 } },
                { id: 'b', x: 230, y: 24, powerPlant: { number: 13 } },
                { id: 'c', x: 165, y: 80, powerPlant: { number: 10 } },
            ],
        });
        const unavailable = () =>
            wrapper.findAll('.unavailable-plant').wrappers.map((w) => w.attributes('data-market-plant'));
        expect(unavailable()).to.deep.equal(['13']);
        expect(wrapper.find('[data-market-highlight]').attributes('height')).to.equal('121');
        expect(wrapper.find('[data-market-highlight]').attributes('pointer-events')).to.equal('none');
        await wrapper.setProps({ chooseablePowerPlants: [13] });
        expect(unavailable()).to.deep.equal(['8', '10']);
        await wrapper.setProps({ canChoose: false });
        expect(unavailable()).to.deep.equal([]);
        expect(wrapper.find('[data-market-highlight]').exists()).to.equal(false);
        await wrapper.setProps({ canChoose: true, chooseablePowerPlants: [] });
        expect(unavailable()).to.deep.equal(['8', '13', '10']);
        expect(wrapper.find('[data-market-highlight]').exists()).to.equal(false);
        wrapper.destroy();
    });
});
