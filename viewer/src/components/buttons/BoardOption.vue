<template>
    <g
        class="button enabled board-option"
        :class="{ active }"
        :data-board-control="control"
        role="button"
        :aria-label="label"
        :aria-pressed="toggle ? (active ? 'true' : 'false') : undefined"
        tabindex="0"
        @click="$emit('click')"
        @keydown.enter.prevent="$emit('click')"
        @keydown.space.prevent="$emit('click')"
    >
        <rect class="option-background board-control-border" :width="width" :height="height" rx="4" stroke="black" />
        <g
            :transform="`translate(${(width - 22) / 2}, ${(height - 22) / 2 - 1})`"
            fill="none"
            stroke="currentColor"
            stroke-width="1.7"
            aria-hidden="true"
        >
            <template v-if="icon === 'shapes'">
                <path d="M6 1L11 9H1Z" />
                <circle cx="16" cy="6" r="4" />
                <rect x="6" y="13" width="8" height="8" />
            </template>
            <template v-else-if="icon === 'regions'">
                <path d="M1 5L7 2L15 5L21 2V18L15 21L7 18L1 21ZM7 2V18M15 5V21" />
            </template>
            <text
                v-else-if="icon === 'text'"
                x="11"
                y="12"
                text-anchor="middle"
                dominant-baseline="central"
                fill="currentColor"
                stroke="none"
                font-size="14"
                font-weight="600"
                translate="no"
                >Aa</text
            >
            <path
                v-else-if="icon === 'rules'"
                d="M3 2H18V20H3Q0 20 0 17V5Q0 2 3 2ZM3 2V16M0 17Q0 15 3 15H18M6 6H14M6 10H14"
            />
            <path v-else-if="icon === 'return'" d="M9 5L3 11L9 17M3 11H14Q20 11 20 17" />
            <path v-else d="M2 2V20H21M5 15L10 8L15 11L21 3M16 3H21V8" />
        </g>
        <path
            v-if="active"
            class="active-marker"
            :d="`M${width / 2 - 5} ${height - 2}H${width / 2 + 5}`"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            aria-hidden="true"
            pointer-events="none"
        />
        <g v-if="badge" aria-hidden="true" pointer-events="none">
            <circle :cx="width - 4" cy="3" r="7" fill="#203a45" stroke="#fff" />
            <text
                :x="width - 4"
                y="3"
                fill="white"
                text-anchor="middle"
                dominant-baseline="central"
                style="font: bold 9px Arial"
                >{{ badge }}</text
            >
        </g>
        <title>{{ label }}</title>
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component
export default class BoardOption extends Vue {
    @Prop() control!: string;
    @Prop() icon!: string;
    @Prop() label!: string;
    @Prop({ default: false }) active!: boolean;
    @Prop({ default: 0 }) badge!: number;
    @Prop({ default: 36 }) width!: number;
    @Prop({ default: 26 }) height!: number;
    @Prop({ default: true }) toggle!: boolean;
}
</script>
<style scoped>
.board-option {
    color: black;
}
.board-option:hover {
    color: black;
}
.option-background {
    fill: gainsboro;
}
.active .option-background {
    fill: #c8d6dc;
}
.board-option:hover .option-background {
    fill: silver;
}

.board-option:focus {
    outline: none;
}
</style>
