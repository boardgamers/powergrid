// Experimental adapter for future hybrid play. Frozen teacher workers stay unchanged.
const assert = require('node:assert/strict');
const { SealedBeliefContinuations } = require('./sealed-belief-continuations.cjs');
const beliefs = require('./sealed-policy-beliefs.cjs');
const encoders = require('./encoders.cjs');
const search = require('./search.cjs');
const c = require('../core.cjs');
const REVISIONS = ['4.2-discard-correction', '4.3-strategic-correction'];

function encoderFor(revision) {
    assert(REVISIONS.includes(revision), 'Unsupported hybrid feature revision');
    return encoders.forRevision(revision);
}

function prepare(q) {
    const encoder = encoderFor(q.featureRevision);
    const state = beliefs.publicState(q.state, q.player);
    const observation = encoder.encode(state, q.player);
    const moves = observation.moves;
    assert.deepEqual(moves, c.candidates(state, q.player));
    delete observation.moves;
    const prior = beliefs.prompts(state, q.player).map(p => {
        const encoded = encoder.encode(p.state, p.actor);
        assert.deepEqual(encoded.moves, p.encoded.moves, 'Belief action order changed');
        return { actor: p.actor, encoded };
    });
    return { observation, moves, options: search.shortlist(state, q.player, 6, true), prior };
}

class HybridContinuations extends SealedBeliefContinuations {
    reset(q) {
        this.hybridEncoder = encoderFor(q.featureRevision);
        // Both supported revisions have identical legal menus. Reuse the frozen
        // scenario/belief logic, then encode every observation in the model's format.
        return super.reset({ ...q, state: beliefs.publicState(q.state, q.player),
            featureRevision: beliefs.REVISION });
    }

    reply() {
        // The parent calls reply during reset, before returning its first batch.
        this.encoder = this.hybridEncoder;
        return super.reply();
    }
}

module.exports = { HybridContinuations, prepare, REVISIONS };
if (require.main === module) {
    const batch = new HybridContinuations();
    (async () => {
        for await (const line of require('node:readline').createInterface({ input: process.stdin })) {
            try {
                const q = JSON.parse(line);
                assert(['prepare', 'reset', 'step'].includes(q.op), 'Unknown operation');
                console.log(JSON.stringify(q.op === 'prepare' ? prepare(q) :
                    q.op === 'reset' ? batch.reset(q) : batch.step(q.actions)));
            } catch (error) {
                console.error(error.stack);
                process.exit(1);
            }
        }
    })();
}
