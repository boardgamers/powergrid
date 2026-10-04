<template>
    <g
        class="button enabled board-option"
        :class="{ active }"
        :data-board-control="control"
        role="button"
        :aria-label="label"
        :aria-pressed="active ? 'true' : 'false'"
        tabindex="0"
        @click="$emit('click')"
        @keydown.enter.prevent="$emit('click')"
        @keydown.space.prevent="$emit('click')"
    >
        <rect class="option-background" width="36" height="26" rx="4" stroke="black" />
        <g transform="translate(7, 2)" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <template v-if="icon === 'shapes'">
                <path d="M6 1L11 9H1Z" />
                <circle cx="16" cy="6" r="4" />
                <rect x="6" y="13" width="8" height="8" />
            </template>
            <template v-else-if="icon === 'regions'">
                <path d="M1 5L7 2L15 5L21 2V18L15 21L7 18L1 21ZM7 2V18M15 5V21" />
            </template>
            <path v-else-if="icon === 'return'" d="M9 5L3 11L9 17M3 11H14Q20 11 20 17" />
            <path v-else d="M2 2V20H21M5 15L10 8L15 11L21 3M16 3H21V8" />
        </g>
        <g v-if="badge" aria-hidden="true" pointer-events="none">
            <circle cx="32" cy="3" r="7" fill="#203a45" stroke="#fff" />
            <text
                x="32"
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
}
</script>
<style scoped>
.board-option {
    color: #253221;
}
.option-background {
    fill: gainsboro;
}
.active .option-background {
    fill: #203a45;
}
.active {
    color: white;
}
.board-option:hover .option-background {
    stroke-width: 2;
}
.board-option:focus {
    outline: none;
}
.board-option:focus-visible .option-background {
    stroke: #fff;
    stroke-width: 3;
}
</style>
