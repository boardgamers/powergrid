<template>
    <g class="resupply-badge" :data-resource="resource" :data-amount="amount">
        <title>Resource Resupply: {{ amount }}</title>
        <rect width="76" height="28" rx="6" fill="#f4e5a8" stroke="#806b28" />
        <component
            :is="resourceIcon"
            :pieceId="-1"
            :targetState="{ x: 5, y: 4 }"
            :canClick="false"
            :transparent="false"
        />
        <text x="69" y="15" text-anchor="end" dominant-baseline="middle" fill="#26351a" style="font: bold 20px Arial"
            >+{{ amount.toString().trim() }}</text
        >
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import Coal from '../pieces/Coal.vue';
import Oil from '../pieces/Oil.vue';
import Garbage from '../pieces/Garbage.vue';
import Uranium from '../pieces/Uranium.vue';

@Component({ components: { Coal, Oil, Garbage, Uranium } })
export default class ResupplyBadge extends Vue {
    @Prop() resource!: string;
    @Prop() amount!: number | string;
    get resourceIcon(): string {
        return this.resource[0].toUpperCase() + this.resource.slice(1);
    }
}
</script>
