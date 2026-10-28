// Correct public information during a complete model resource turn.
// Historical runtime remains unchanged; callers must pin this adapter separately.
const assert = require('node:assert/strict');
const path = require('node:path');

function createModelResourceTurn(runtimeDirectory) {
    const runtime=path.resolve(runtimeDirectory);
    const {ModelResourceTurn}=require(path.join(runtime,'ai/strong/resource-turn-search-v1.cjs'));
    return class PublicModelResourceTurn extends ModelResourceTurn {
        step(index) {
            const metadata={cardsLeft:this.g.cardsLeft,nextCardWeak:this.g.nextCardWeak};
            const result=super.step(index);
            if(this.done)return result;
            assert.equal(this.g.map.name,'Germany');assert.equal(this.g.phase,'Resources');
            assert.deepEqual(this.g.currentPlayers,[this.seat]);
            // The engine derives these facts from the deck on every move. This
            // public simulation has no deck, and a purchase cannot change them.
            Object.assign(this.g,metadata);
            return this.reply();
        }
    };
}

module.exports={revision:'resource-model-turn-v2',createModelResourceTurn};
