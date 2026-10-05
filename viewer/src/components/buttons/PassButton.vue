<template>
    <g
        :class="['button', { enabled, highlightButton }]"
        data-board-control="pass"
        role="button"
        :aria-label="text"
        :tabindex="enabled ? 0 : -1"
        :aria-disabled="!enabled"
        @click="enabled && $emit('click')"
        @keydown.enter.prevent="enabled && $emit('click')"
        @keydown.space.prevent="enabled && $emit('click')"
    >
        <rect width="80" height="26" fill="gainsboro" stroke="black" rx="2" />
        <path
            :d="iconPath"
            transform="translate(30, 4)"
            fill="none"
            stroke="black"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
        />
        <title>{{ text }}</title>
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component
export default class PassButton extends Vue {
    @Prop() enabled!: boolean;
    @Prop() highlightButton!: boolean;
    @Prop() text!: string;
    @Prop({ default: 'done' }) icon!: string;

    get iconPath(): string {
        const paths: Record<string, string> = {
            auction: 'M2 4L6 0L12 6L8 10Z M9 7L16 14 M0 16H10',
            resources: 'M1 6H16L14 16H3Z M5 6L8 0L12 6',
            building: 'M0 7L8 0L16 7 M2 6V16H14V6 M6 16V10H10V16',
            powering: 'M10 0L2 10H8L6 17L15 6H9Z',
            edit: 'M2 11L12 1L16 5L6 15L1 16Z M10 3L14 7',
            done: 'M1 9L6 14L16 2',
        };
        return paths[this.icon] || paths.done;
    }
}
</script>
