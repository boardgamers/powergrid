<template>
    <g class="calculator">
        <rect width="130" height="210" rx="2" />
        <rect x="10" y="10" width="110" height="30" fill="yellowgreen" rx="2" />
        <text class="visor" x="110" y="25" fill="black" text-anchor="end">{{ value }}</text>
        <rect class="button" x="10" y="50" width="30" height="30" fill="gray" rx="2" @click="add(7)" />
        <text x="25" y="65" fill="white" stroke="white" text-anchor="middle">7</text>
        <rect class="button" x="50" y="50" width="30" height="30" fill="gray" rx="2" @click="add(8)" />
        <text x="65" y="65" fill="white" stroke="white" text-anchor="middle">8</text>
        <rect class="button" x="90" y="50" width="30" height="30" fill="gray" rx="2" @click="add(9)" />
        <text x="105" y="65" fill="white" stroke="white" text-anchor="middle">9</text>
        <rect class="button" x="10" y="90" width="30" height="30" fill="gray" rx="2" @click="add(4)" />
        <text x="25" y="105" fill="white" stroke="white" text-anchor="middle">4</text>
        <rect class="button" x="50" y="90" width="30" height="30" fill="gray" rx="2" @click="add(5)" />
        <text x="65" y="105" fill="white" stroke="white" text-anchor="middle">5</text>
        <rect class="button" x="90" y="90" width="30" height="30" fill="gray" rx="2" @click="add(6)" />
        <text x="105" y="105" fill="white" stroke="white" text-anchor="middle">6</text>
        <rect class="button" x="10" y="130" width="30" height="30" fill="gray" rx="2" @click="add(1)" />
        <text x="25" y="145" fill="white" stroke="white" text-anchor="middle">1</text>
        <rect class="button" x="50" y="130" width="30" height="30" fill="gray" rx="2" @click="add(2)" />
        <text x="65" y="145" fill="white" stroke="white" text-anchor="middle">2</text>
        <rect class="button" x="90" y="130" width="30" height="30" fill="gray" rx="2" @click="add(3)" />
        <text x="105" y="145" fill="white" stroke="white" text-anchor="middle">3</text>
        <rect class="button" x="10" y="170" width="30" height="30" fill="gray" rx="2" @click="add(0)" />
        <text x="25" y="185" fill="white" stroke="white" text-anchor="middle">0</text>
        <rect class="button" x="50" y="170" width="30" height="30" fill="orange" rx="2" @click="del()" />
        <text x="65" y="185" fill="white" text-anchor="middle">Del</text>
        <rect class="button" x="90" y="170" width="30" height="30" fill="orange" rx="2" @click="bid()" />
        <text x="105" y="185" fill="white" text-anchor="middle">Bid</text>
    </g>
</template>
<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';

@Component
export default class Calculator extends Vue {
    value: number = 0;

    add(number) {
        this.value = Math.min(999, this.value * 10 + number);
    }

    del() {
        this.value = Math.floor(this.value / 10);
    }

    bid() {
        this.$emit('bid', this.value);
        this.value = 0;
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
