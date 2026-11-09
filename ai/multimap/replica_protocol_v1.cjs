'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Independent literals, never trust an import-time copy of mutable study JSON.
const frozenSources = Object.freeze({
    'expert-protocol-v2.json': 'd9180c76ce072fe03fb1c325466d8d768a919d040ffd27229d4f375f61065796',
    'expert_ppo.py': '4357357fde973deff89d9df908622297ccce6fb89446c6e4cf314f20a5383bd0',
    'expert_rollout.py': '3deb6af55d5210caa04d02210a14bd3ff9c7af413afa2b39ef72bb3e3ebfb77e',
    'expert_game.cjs': '6d0580b5054e5fb18b5b872827796665125d9997dd31b720dfe2becb00369942',
    'expert_policy.py': '5304112f56195eec7aa6f89967503e6d08768be7ffb4fc232a7fcfe3349b4213',
    'job_expert.py': '58a1d8bfe189228f48a4f139e4b8727a58cdfd65d8efd0ff6a8d0e182c24a8cb',
    'teacher_v2.cjs': '89a5b6c9e8520224eeb1cb34d8543cfccb2d8313002626a50907d4fa996cbdf6',
    'economics_v2.cjs': 'dbb2216b3572e4afc882a3da11f683abd998a54b8672c7acda4843ee142d1897',
    'candidate-pool-v1.json': 'a4f5d80966d9dd5b7af712459dffea255590eeb158b3a8e73cb66b0045d29a4b',
});
const critical = {
    schema: 'multimap-expert-replicas-v1',
    baseProtocol: 'expert-protocol-v2.json',
    frozenSources,
    replicas: [
        { id: 1, seed: 190731, seedNamespace: 'pg-multimap-expert-replicas-v1-r1' },
        { id: 2, seed: 827119, seedNamespace: 'pg-multimap-expert-replicas-v1-r2' },
    ],
    transferMaps: [],
    qualificationEligible: false,
    reservedFinalSeedsUsed: false,
    counts: {
        trainingGamesPerReplica: 2720,
        selectionGamesPerReplica: 2240,
        confirmationGamesPerArmPerReplica: 640,
        confirmationDealRootsPerReplica: 160,
        totalGamesPerReplica: 6240,
        totalGames: 12480,
    },
    analysis: {
        primary: 'selected-minus-teacher-v2',
        unit: 'paired-all-seat-deal',
        weighting: 'equal-80-map-count-rule-cells',
        dealsPerCell: 2,
        normal95Z: 1.96,
        pooledInference: false,
        winnerSelection: false,
        betweenReplicaSpread: 'descriptive-includes-evaluation-noise',
    },
    budget: {
        replicas: 2,
        workers: 6,
        flavor: 'cpu-upgrade',
        timeout: '3h',
        maxSegmentsPerReplica: 2,
        maxTotalJobHours: 12,
        studyArtifactMaxBytes: 134217728,
        localStorageMaxBytes: 8589934592,
        minimumFreeBytes: 2147483648,
    },
};
function canonical(value) {
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    if (value !== null && typeof value === 'object') {
        return (
            '{' +
            Object.keys(value)
                .sort()
                .map((key) => JSON.stringify(key) + ':' + canonical(value[key]))
                .join(',') +
            '}'
        );
    }
    return JSON.stringify(value);
}
module.exports = function protocol(id) {
    if (!['1', '2'].includes(id)) throw Error('Replica must be 1 or 2');
    // Read every time: the require cache must not hide protocol-file drift.
    const study = JSON.parse(fs.readFileSync(path.join(__dirname, 'expert-replicas-protocol-v1.json'), 'utf8'));
    if (
        !study ||
        typeof study !== 'object' ||
        Array.isArray(study) ||
        Object.keys(critical).some((key) => !Object.hasOwn(study, key))
    ) {
        throw Error('Missing critical replica protocol fields');
    }
    const observed = Object.fromEntries(Object.keys(critical).map((key) => [key, study[key]]));
    if (canonical(observed) !== canonical(critical)) throw Error('Frozen replica protocol scope/pins/budget changed');
    for (const [name, sha] of Object.entries(frozenSources)) {
        const actual = crypto
            .createHash('sha256')
            .update(fs.readFileSync(path.join(__dirname, name)))
            .digest('hex');
        if (actual !== sha) throw Error('Frozen expert source changed');
    }
    const base = JSON.parse(fs.readFileSync(path.join(__dirname, 'expert-protocol-v2.json'), 'utf8'));
    const replica = critical.replicas[Number(id) - 1];
    return { ...base, seed: replica.seed, seedNamespace: replica.seedNamespace, transferMaps: [] };
};
