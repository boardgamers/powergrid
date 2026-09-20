<template>
    <section class="round-planner" aria-label="Round planning">
        <template v-if="plan">
            <div class="planner-strip">
                <div v-if="queueable || hasQueue" class="planner-controls">
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
                    <button v-if="hasQueue" :disabled="pending" @click="$emit('cancel')">Cancel premoves</button>
                </div>
            </div>
            <p v-if="!queueable && queueHint" class="muted queue-hint">{{ queueHint }}</p>
            <p v-if="liveChanged" class="notice">
                The live game changed. Costs and fuel will be checked again before queueing.
            </p>
            <p v-if="plan.finalScoring" class="muted">
                The end-game threshold is reached. Final scoring uses the most cities you can power with your fuel;
                there is no normal income payment.
            </p>
        </template>
        <p v-if="pending" role="status">Saving premoves…</p>
        <p v-if="error" role="status" class="notice">{{ error }}</p>
    </section>
</template>
<script lang="ts">
import Vue from 'vue';
import type { RoundPlan } from 'powergrid-engine/src/planning';
import type { PremovePlan } from 'powergrid-engine/src/premoves';
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
    computed: {
        hasQueue(): boolean {
            return !!this.queue?.phases.length;
        },
    },
});
</script>
<style scoped>
.round-planner,
.planner-strip {
    display: contents;
}
.planner-controls {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    padding: 5px 10px 5px 0;
    font: 14px Arial, sans-serif;
    color: #f0f2e9;
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
.round-planner > p {
    flex-basis: 100%;
    padding: 0 12px;
    margin: 0 0 8px;
    font: 13px Arial, sans-serif;
}
.muted {
    color: #bcc7ad;
    font-size: 13px;
}
button:focus-visible {
    outline: 2px solid #d7ed95;
    outline-offset: 2px;
}
.queue-hint {
    margin: 7px 0 0;
}
.notice {
    color: #efcb88;
}
</style>
