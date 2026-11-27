import { expect } from 'chai';
import { BULBS, holidayLook, isChristmasSeason } from '../../src/util/holiday';

const day = (y: number, m: number, d: number) => new Date(y, m - 1, d, 12);

describe('Christmas houses', () => {
    it('is the season from December 1 through January 6, every year', () => {
        expect(isChristmasSeason(day(2026, 11, 30))).to.equal(false);
        expect(isChristmasSeason(day(2026, 12, 1))).to.equal(true);
        expect(isChristmasSeason(day(2026, 12, 25))).to.equal(true);
        expect(isChristmasSeason(day(2026, 12, 31))).to.equal(true);
        expect(isChristmasSeason(day(2027, 1, 6))).to.equal(true);
        expect(isChristmasSeason(day(2027, 1, 7))).to.equal(false);
        expect(isChristmasSeason(day(2031, 12, 10))).to.equal(true);
        expect(isChristmasSeason(day(2031, 7, 4))).to.equal(false);
    });

    it('is on by default in season, and never out of season', () => {
        expect(holidayLook(undefined, day(2026, 12, 15), false)).to.equal('lively');
        expect(holidayLook({}, day(2026, 12, 15), false)).to.equal('lively');
        expect(holidayLook({ holidayDecorations: 'on' }, day(2026, 6, 15), false)).to.equal('none');
    });

    it("follows the viewer's setting: on, calm or off", () => {
        const dec = day(2026, 12, 15);
        expect(holidayLook({ holidayDecorations: 'on' }, dec, false)).to.equal('lively');
        expect(holidayLook({ holidayDecorations: 'calm' }, dec, false)).to.equal('still');
        expect(holidayLook({ holidayDecorations: 'off' }, dec, false)).to.equal('none');
    });

    it('keeps the lights still when the device asks for reduced motion', () => {
        const dec = day(2026, 12, 15);
        expect(holidayLook({ holidayDecorations: 'on' }, dec, true)).to.equal('still');
        expect(holidayLook({ holidayDecorations: 'off' }, dec, true)).to.equal('none');
    });

    it('strings the lights along the roofline in four alternating colours', () => {
        expect(BULBS.length).to.be.greaterThan(12);
        expect(new Set(BULBS.map((b) => b.color)).size).to.equal(4);
        expect(BULBS.filter((b) => b.alternate).length).to.be.closeTo(BULBS.length / 2, 1);
        for (const b of BULBS) {
            expect(b.x).to.be.within(0, 400);
            expect(b.y).to.be.within(0, 280);
        }
    });
});

describe('Holiday board button', () => {
    it('cycles On -> Calm -> Off -> On, starting from On when never set', async () => {
        const { nextHolidaySetting } = await import('../../src/util/holiday');
        expect(nextHolidaySetting(undefined)).to.equal('calm');
        expect(nextHolidaySetting('on')).to.equal('calm');
        expect(nextHolidaySetting('calm')).to.equal('off');
        expect(nextHolidaySetting('off')).to.equal('on');
    });

    it('only shows in season, by the viewer clock', async () => {
        const { inHolidaySeason, setHolidayClock } = await import('../../src/util/holiday');
        setHolidayClock(() => day(2026, 12, 2));
        expect(inHolidaySeason()).to.equal(true);
        setHolidayClock(() => day(2027, 1, 7));
        expect(inHolidaySeason()).to.equal(false);
        setHolidayClock(() => new Date());
    });
});
