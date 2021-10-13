<template>
    <g :id="elId" :class="['loan', { dragging, canDrag }]" :transform="`translate(${currentX}, ${currentY})`">
        <rect width="30" height="60" fill="royalblue" stroke="white" stroke-width="2" rx="2" />
        <g transform="translate(33, -10) rotate(280, 15, 30)">
            <text text-anchor="middle" fill="white">Loan</text>
        </g>
        <title v-if="owner == -1">Get Loan</title>
        <title v-else-if="owner == player">Pay Loan</title>
    </g>
</template>
<script lang="ts">
import { PieceType } from '@/types/ui-data';
import { Component, Mixins, Prop } from 'vue-property-decorator';
import Piece from './Piece.vue';

@Component({
    created(this: LoanCard) {
        this.pieceType = PieceType.Loan;
    }
})
export default class LoanCard extends Mixins(Piece) {
    @Prop()
    owner?: number;

    @Prop()
    player?: number;
}
</script>
<style lang="scss">
.loan {
    &:not(.dragging) {
        transition-property: transform;
        transition-duration: 0.8s;
        transition-timing-function: ease-in-out;
    }

    &.canDrag {
        cursor: pointer;

        rect {
            &:hover {
                stroke: white;
            }
        }
    }
}
</style>
