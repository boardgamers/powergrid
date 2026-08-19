<template>
    <g class="button enabled" @click="$emit('click')">
        <circle cx="15" cy="15" r="15" fill="gainsboro" stroke="black" stroke-width="2px" />
        <!-- Stacked: three full-width rows. Wide: the authored side-by-side board. -->
        <template v-if="isOn">
            <rect x="6" y="7" width="18" height="4" rx="1" fill="black" />
            <rect x="6" y="13" width="18" height="4" rx="1" fill="black" />
            <rect x="6" y="19" width="18" height="4" rx="1" fill="black" />
        </template>
        <template v-else>
            <rect x="6" y="7" width="10" height="16" rx="1" fill="black" />
            <rect x="18" y="7" width="6" height="7" rx="1" fill="black" />
            <rect x="18" y="16" width="6" height="7" rx="1" fill="black" />
        </template>
        <title v-if="isOn">Switch to the full board layout</title>
        <title v-else>Stack the board into rows</title>
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component
export default class LayoutButton extends Vue {
    @Prop()
    isOn?: boolean;
}
</script>
