<template>
    <g
        :id="elId"
        :class="[{ canClick: canClick }]"
        :transform="`translate(${currentX}, ${currentY})`"
        :opacity="transparent ? 0.3 : 1"
        @click="canClick && $emit('click')"
    >
        <path d="M2,5 A9,5,0 0,1 18,5 L18,15 A9,5 0 0,1 2,15Z" fill="none" stroke="black" stroke-miterlimit="0" />
        <path d="M2,5 A9,5 0 0,0 18,5 A9,5 0 0,0 2,5" fill="#FF0" />
        <path d="M2,5 A9,5 0 0,0 2,5 L2,15 A9,5,0 0,0 18,15 L18,5 A9,5 0 0,1 2,5" fill="url(#garbage-linear)" />

        <title>Garbage</title>

        <defs>
            <linearGradient id="garbage-linear" x1="0" y1="10" x2="20" y2="10" gradientUnits="userSpaceOnUse">
                <stop stop-color="#DD0" />
                <stop offset="1" stop-color="#AA0" />
            </linearGradient>
        </defs>
    </g>
</template>
<script lang="ts">
import { PieceType } from '@/types/ui-data';
import { Component, Mixins, Prop } from 'vue-property-decorator';
import Piece from './Piece.vue';

@Component({
    created(this: Garbage) {
        this.pieceType = PieceType.Garbage;
    }
})
export default class Garbage extends Mixins(Piece) {
    @Prop()
    canClick?: boolean;
}
</script>
