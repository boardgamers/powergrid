<template>
    <g class="calculator">
        <rect width="125" height="50" rx="4" />
        <rect x="10" y="10" width="30" height="30" fill="lime" rx="2" />
        <text class="visor" x="25" y="25" fill="black" text-anchor="middle">{{ value }}</text>
        <g :style="value < maxValue ? 'cursor: pointer' : ''" @click="add()">
            <rect x="48" y="7" width="24" height="15" fill="gray" stroke="gray" rx="2" />
            <path d="M52,17 l8,-6 l8,6" fill="none" stroke="white" stroke-width="3" />
        </g>
        <g :style="value > minValue ? 'cursor: pointer' : ''" @click="sub()">
            <rect x="48" y="28" width="24" height="15" fill="gray" stroke="gray" rx="2" />
            <path d="M52,32 l8,6 l8,-6" fill="none" stroke="white" stroke-width="3" />
        </g>
        <g style="cursor: pointer" @click="bid()">
            <rect class="button" x="80" y="7" width="36" height="36" fill="gray" rx="2" />
            <text x="97" y="25" fill="white" text-anchor="middle">OK</text>
        </g>
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component({
    created(this: Calculator) {
        this.value = this.minValue;
    }
})
export default class Calculator extends Vue {
    @Prop()
    minValue;

    @Prop()
    maxValue;

    value: number = 0;

    add() {
        this.value = Math.min(this.maxValue, this.value + 1);
    }

    sub() {
        this.value = Math.max(this.minValue, this.value - 1);
    }

    bid() {
        this.$emit('bid', this.value);
        this.value++;
    }
}
</script>
<style lang="scss">
.calculator {
    fill: #333;

    .button {
        cursor: pointer;
    }

    .visor {
        font-family: 'system-ui';
    }
}
</style>
