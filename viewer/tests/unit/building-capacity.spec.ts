import { mount } from '@vue/test-utils';
import { expect } from 'chai';
import { Phase } from 'powergrid-engine';
import Game from '@/components/Game.vue';
import CityCount from '@/components/boards/CityCount.vue';

const capacity = (context: any) => (Game as any).options.computed.buildingPowerCapacity.get.call(context);

describe('building power capacity', () => {
    it('shows the viewing player’s total plant output only during building', () => {
        const G = {
            phase: Phase.Building,
            players: [
                { powerPlants: [{ citiesPowered: 2 }, { citiesPowered: 4 }, { citiesPowered: 6 }] },
                { powerPlants: [{ citiesPowered: 3 }] },
            ],
        };
        expect(capacity({ G, player: 0 })).to.equal(12);
        expect(capacity({ G, player: 1 })).to.equal(3);
        expect(capacity({ G, player: undefined })).to.equal(undefined);
        expect(capacity({ G, player: -1 })).to.equal(undefined);
        expect(capacity({ G: { ...G, phase: Phase.Bureaucracy }, player: 0 })).to.equal(undefined);
    });

    it('marks capacity, caps the track position, and restores the powering marker', async () => {
        const wrapper = mount(CityCount, {
            propsData: { paymentTable: Array.from({ length: 22 }, (_, i) => i * 10), powerCapacity: 12 },
            stubs: ['House'],
        });
        expect(wrapper.find('.city-income-legend').text()).to.contain('Power capacity: 12 cities');
        expect(wrapper.find('.power-capacity-marker').element.parentElement!.getAttribute('transform')).to.equal(
            'translate(396, 0)'
        );
        await wrapper.setProps({ powerCapacity: 30, compact: true });
        expect(wrapper.find('.power-capacity-marker').element.parentElement!.getAttribute('transform')).to.equal(
            'translate(330, 70)'
        );
        expect(wrapper.find('.city-income-legend').text()).to.contain('Power capacity: 30 cities');
        await wrapper.setProps({ powerCapacity: undefined, poweredCities: 8, ownedCities: 10, poweringIncome: 90 });
        expect(wrapper.find('.power-capacity-marker').exists()).to.equal(false);
        expect(wrapper.find('.powered-city-marker').exists()).to.equal(true);
        expect(wrapper.find('.city-income-legend').text()).to.contain('8 / 10 cities powered');
        wrapper.destroy();
    });
});
