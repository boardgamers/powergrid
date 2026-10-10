// Additional reference opponents; old opponent identities remain unchanged.
const core = require('../core.cjs'), old = require('./economics.cjs'),
    capacity = require('./economics-v4_1.cjs'), menu = require('./features-v4_sealed.cjs');
function choose(g, seat, rng = () => 0.5, corrected = false) {
    const policy = corrected ? capacity : old;
    if (!g.options.fastBid) return policy.choose(g, seat, rng);
    const actions = menu.candidates(g, seat), values = policy.scores(g, seat, actions);
    let index = 0, best = -Infinity;
    values.forEach((value, i) => {
        value += rng() * .001;
        if (value > best) {best = value; index = i;}
    });
    return {index, action: actions[index]};
}
module.exports = {choose};
