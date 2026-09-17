<template>
    <section class="round-planner" :class="{ active: plan, compact: !plan && !hasQueue }" aria-label="Round planning">
        <template v-if="plan">
            <div class="planner-strip">
                <div class="planner-controls">
                    <span
                        class="preview-label"
                        title="Use the normal board controls. No move is sent until you confirm a queue. The preview does not predict hidden plant draws."
                        >Preview only</span
                    >
                    <button :disabled="!plan.entries.length" @click="$emit('clear')">Start over</button>
                    <button v-if="plan.state.phase === 'Auction' && !discarding" @click="$emit('skip-plant')">
                        Continue without buying
                    </button>
                    <button
                        v-if="queueable"
                        class="primary"
                        :disabled="pending"
                        :title="
                            playsNow
                                ? 'Play this phase and queue the remaining moves'
                                : 'Queue these moves for your turn'
                        "
                        @click="$emit('queue')"
                    >
                        Validate
                    </button>
                    <button v-if="hasQueue" :disabled="pending" @click="$emit('cancel')">Cancel queued moves</button>
                </div>
            </div>
            <p v-if="!queueable && queueHint" class="muted queue-hint">{{ queueHint }}</p>
            <p v-if="plan.state.phase === 'Auction' && !discarding" class="muted">
                Choose a plant, then use the bid control to enter an assumed winning price. No bid is sent.
            </p>
            <p v-if="liveChanged" class="notice">
                The live game changed. Costs and fuel will be checked again before queueing. Start over to recalculate
                the preview.
            </p>
            <p v-if="plan.finalScoring" class="muted">
                The end-game threshold is reached. Final scoring uses the most cities you can power with your fuel;
                there is no normal income payment.
            </p>
        </template>
        <template v-else-if="hasQueue">
            <div class="planner-heading">
                <strong>Your premoves · round {{ queue.round }}</strong>
                <div class="planner-controls">
                    <button :disabled="pending" @click="$emit('cancel')">Cancel all</button>
                </div>
            </div>
            <div v-for="phase in queue.phases" :key="phase.phase" class="queued-phase">
                <strong>{{ phaseName(phase.phase) }}</strong
                ><span>{{
                    phase.moves
                        .filter((move) => move.name !== 'Pass')
                        .map(describeMove)
                        .join(' · ') ||
                    (phase.phase === 'Building' ? 'Finish without building' : 'Finish without powering')
                }}</span>
            </div>
        </template>
        <p v-if="queue && queue.notice" role="status" class="notice">{{ queue.notice }}</p>
        <p v-if="pending" role="status">Saving premoves…</p>
        <p v-if="error" role="status" class="notice">{{ error }}</p>
    </section>
</template>
<script lang="ts">
import Vue from 'vue';
import type { RoundPlan } from 'powergrid-engine/src/planning';
import type { PremovePlan } from 'powergrid-engine/src/premoves';
import { describeMove } from '../util/round-plan';
export default Vue.extend({
    props: {
        plan: { type: Object as () => RoundPlan | null, default: null },
        queue: { type: Object as () => PremovePlan | undefined, default: undefined },
        liveChanged: Boolean,
        queueable: Boolean,
        playsNow: Boolean,
        pending: Boolean,
        error: String,
        queueHint: String,
    },
    methods: { describeMove, phaseName: (phase: string) => (phase === 'Bureaucracy' ? 'Powering' : phase) },
    computed: {
        hasQueue(): boolean {
            return !!this.queue?.phases.length;
        },
        discarding(): boolean {
            const moves = this.plan?.state.players[this.plan.seat].availableMoves;
            return !!(moves?.DiscardPowerPlant || moves?.DiscardResources);
        },
    },
});
</script>
<style scoped>
.round-planner {
    align-self: stretch;
    box-sizing: border-box;
    width: 100%;
    font-family: Arial, sans-serif;
    background: #171c13;
    color: #f0f2e9;
    border-bottom: 2px solid #9acd32;
    padding: 8px 20px 10px;
    font-size: 14px;
    text-align: left;
}
.round-planner.compact {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 16px;
    background: #171c13;
    padding: 6px 14px;
    flex-wrap: wrap;
}
.planner-heading,
.planner-controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    flex-wrap: wrap;
}
.planner-heading strong {
    font-size: 17px;
}
p {
    margin: 6px 0;
}
button {
    font: inherit;
    border: 1px solid #68725f;
    border-radius: 3px;
    background: transparent;
    color: inherit;
    padding: 5px 10px;
    cursor: pointer;
}
button:hover {
    background: #35412b;
}
button:disabled {
    opacity: 0.45;
    cursor: default;
}
.primary {
    background: #9acd32;
    color: #182007;
    border-color: #9acd32;
    font-weight: 600;
}
.primary:hover {
    background: #b0df52;
}
.round-planner.active,
.planner-strip {
    display: contents;
}
.round-planner.active .planner-controls {
    padding: 5px 10px 5px 0;
}
.round-planner.active > p {
    flex-basis: 100%;
    padding: 0 12px;
    margin: 0 0 8px;
    font: 13px Arial, sans-serif;
}
.planner-controls {
    justify-content: flex-start;
}
.muted {
    color: #bcc7ad;
    font-size: 13px;
}
button:focus-visible {
    outline: 2px solid #d7ed95;
    outline-offset: 2px;
}
.preview-label {
    font-size: 12px;
    color: #d7ed95;
    margin-right: 4px;
}
.queue-hint {
    margin: 7px 0 0;
}
.queued-phase {
    display: flex;
    gap: 14px;
    align-items: baseline;
    flex-wrap: wrap;
    padding: 8px 0;
}
.queued-phase > span {
    flex: 1;
}
.queued-phase button {
    font-size: 12px;
}
.notice {
    color: #efcb88;
}
@media (max-width: 600px) {
    .round-planner {
        padding: 12px;
    }
    .planner-heading strong {
        font-size: 16px;
    }
}
</style>
