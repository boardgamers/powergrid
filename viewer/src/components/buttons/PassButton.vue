<template>
    <g
        :class="['button', { enabled, highlightButton, 'skip-action': action === 'skip' }]"
        data-board-control="pass"
        role="button"
        :aria-label="text"
        :tabindex="enabled ? 0 : -1"
        :aria-disabled="!enabled"
        @click="enabled && $emit('click')"
        @keydown.enter.prevent="enabled && $emit('click')"
        @keydown.space.prevent="enabled && $emit('click')"
    >
        <path class="phase-background" d="M4 0H76Q80 0 80 4V22Q80 26 76 26H4Q0 26 0 22V4Q0 0 4 0Z" fill="gainsboro" />
        <path class="button-divider" d="M40 0V26" stroke="#88949a" aria-hidden="true" />
        <path
            :d="iconPath"
            data-phase-icon
            transform="translate(12, 5)"
            fill="none"
            stroke="black"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
        />
        <path
            :d="actionPath"
            data-action-icon
            transform="translate(52, 5)"
            fill="none"
            stroke="black"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
        />
        <!-- Paint the shared outline last so neither half can cover the highlight. -->
        <rect
            class="button-outline board-control-border turn-action-border"
            width="80"
            height="26"
            fill="none"
            stroke="black"
            rx="4"
            pointer-events="none"
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
    @Prop({ default: 'finish' }) action!: string;

    get actionPath(): string {
        const paths: Record<string, string> = {
            skip: 'M16 8A8 8 0 1 1 0 8A8 8 0 1 1 16 8Z M2.34 2.34L13.66 13.66',
            finish: 'M1 9L6 14L16 2',
            edit: 'M2 11L12 1L16 5L6 15L1 16Z M10 3L14 7',
        };
        return paths[this.action] || paths.finish;
    }

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

<style scoped>
/* Match the color-blind/simulation controls: one grey surface, black border,
   then silver with a white border on hover. Keep the icons unchanged. */
.button .button-outline {
    fill: none;
}
.button.enabled:hover .phase-background {
    fill: silver;
}
.button.enabled:hover .button-divider {
    stroke: #59666c;
}
.button.enabled:hover .button-outline,
.button.enabled:focus-visible .button-outline {
    fill: none;
}
</style>
