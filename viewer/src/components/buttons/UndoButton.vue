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
        <rect
            class="undo-background board-control-border turn-action-border"
            :width="width"
            :height="height"
            fill="gainsboro"
            stroke="black"
            rx="4"
        />
        <ActionLabel v-if="showText" :text="text" :width="width" :height="height" />
        <image
            v-else-if="icon === 'undo'"
            data-action-icon
            :x="width / 2 - 10"
            :y="height / 2 - 10"
            width="20"
            height="20"
            href="../../icons/undo.svg"
            aria-hidden="true"
        />
        <path
            v-else
            data-action-icon
            d="M-7 -7L7 7 M7 -7L-7 7"
            :transform="`translate(${width / 2}, ${height / 2})`"
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
import ActionLabel from './ActionLabel.vue';

@Component({ components: { ActionLabel } })
export default class UndoButton extends Vue {
    @Prop({ default: 'Undo last move' }) text!: string;
    @Prop() enabled!: boolean;
    @Prop() highlightButton!: boolean;
    @Prop({ default: 'undo' }) control!: string;
    @Prop({ default: 'undo' }) icon!: 'undo' | 'cancel';
    @Prop({ default: false }) showText!: boolean;
    @Prop({ default: 80 }) width!: number;
    @Prop({ default: 26 }) height!: number;
}
</script>
