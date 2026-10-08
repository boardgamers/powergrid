<template>
    <g
        :class="['button', { enabled, highlightButton }]"
        :data-board-control="control"
        role="button"
        :aria-label="text"
        :tabindex="enabled ? 0 : -1"
        :aria-disabled="!enabled"
        @click="enabled && $emit('click')"
        @keydown.enter.prevent="enabled && $emit('click')"
        @keydown.space.prevent="enabled && $emit('click')"
    >
        <rect width="80" height="26" fill="gainsboro" stroke="black" rx="2" />
        <image
            v-if="icon === 'undo'"
            x="30"
            y="3"
            width="20"
            height="20"
            href="../../icons/undo.svg"
            aria-hidden="true"
        />
        <path
            v-else
            d="M33 6L47 20 M47 6L33 20"
            stroke="black"
            stroke-width="2"
            stroke-linecap="round"
            aria-hidden="true"
        />
        <title>{{ text }}</title>
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component
export default class UndoButton extends Vue {
    @Prop({ default: 'Undo last move' }) text!: string;
    @Prop() enabled!: boolean;
    @Prop() highlightButton!: boolean;
    @Prop({ default: 'undo' }) control!: string;
    @Prop({ default: 'undo' }) icon!: 'undo' | 'cancel';
}
</script>
