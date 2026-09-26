<template>
    <g
        :class="['button', { enabled, highlightButton }]"
        data-board-control="undo"
        role="button"
        aria-label="Undo last move"
        :tabindex="enabled ? 0 : -1"
        :aria-disabled="!enabled"
        @click="enabled && $emit('click')"
        @keydown.enter.prevent="enabled && $emit('click')"
        @keydown.space.prevent="enabled && $emit('click')"
    >
        <rect width="80" height="26" fill="gainsboro" stroke="black" rx="2" />
        <image x="30" y="3" width="20" height="20" href="../../icons/undo.svg" aria-hidden="true" />
        <title>Undo last move</title>
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component
export default class UndoButton extends Vue {
    @Prop() enabled!: boolean;
    @Prop() highlightButton!: boolean;
}
</script>
