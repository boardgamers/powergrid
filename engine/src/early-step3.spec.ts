import { expect } from 'chai';
import 'mocha';
import { addPowerPlant, reconstructionOptions, setup } from './engine';
import { GameOptions, GameState, Phase } from './gamestate';

// The Step 3 card drawn while the game is still in Step 1: Step 2's setup runs first,
// then Step 3's, back to back.
function drawStep3Early(options: GameOptions, phase: Phase): GameState {
    const G = setup(4, options, 'early-step-3');
    const step3 = G.powerPlantsDeck.find((p) => p.number == 99)!;
    G.powerPlantsDeck = [step3, ...G.powerPlantsDeck.filter((p) => p.number != 99)];
    G.phase = phase;
    // A draw always refills a gap: here the end of the round sends the largest plant under the deck.
    G.futureMarket.pop();
    addPowerPlant(G);
    return G;
}

const market = (G: GameState) => [...G.actualMarket, ...G.futureMarket].map((p) => p.number);
const events = (G: GameState) => G.log.filter((item) => item.type == 'event').map((item) => (item as any).event);

describe('Step 3 card drawn before Step 2', () => {
    it('begins Step 2 first on Spain & Portugal, returning the held-back plants', () => {
        const G = drawStep3Early({ map: 'Spain & Portugal', variant: 'recharged' }, Phase.Bureaucracy);
        const log = events(G);
        const step2 = log.findIndex((e) => e.startsWith('Starting Step 2 (the Step 3 card came first)'));
        const step3 = log.findIndex((e) => e.startsWith('Step 3 will begin next phase'));
        expect(step2, log.join('\n')).to.be.greaterThan(-1);
        expect(step3).to.be.greaterThan(step2);
        // Step 2's replacement draw takes 18 from the top; 22 and 27 are shuffled in.
        expect(market(G)).to.include(18);
        const deck = G.powerPlantsDeck.map((p) => p.number);
        expect(deck).to.include.members([22, 27]);
    });

    it('waits for the end of the auction when drawn during it', () => {
        const G = drawStep3Early({ map: 'Spain & Portugal', variant: 'recharged' }, Phase.Auction);
        expect(G.step).to.equal(1);
        expect(G.futureMarket.map((p) => p.number)).to.include(99);
    });

    it('begins Step 2 first on a standard map', () => {
        const G = drawStep3Early({ map: 'USA', variant: 'recharged' }, Phase.Bureaucracy);
        expect(events(G).some((e) => e.startsWith('Starting Step 2 (the Step 3 card came first)'))).to.be.true;
    });

    it('keeps the old sequence for games created before the rule', () => {
        const options = reconstructionOptions({ map: 'Spain & Portugal', variant: 'recharged' });
        expect(options.step2BeforeStep3).to.equal(false);
        const G = drawStep3Early(options, Phase.Bureaucracy);
        expect(events(G).some((e) => e.startsWith('Starting Step 2'))).to.be.false;
        expect(market(G)).to.not.include(18);
    });

    it('stores the rule on new games', () => {
        expect(setup(4, { map: 'USA', variant: 'recharged' }, 's').options.step2BeforeStep3).to.equal(true);
    });
});
