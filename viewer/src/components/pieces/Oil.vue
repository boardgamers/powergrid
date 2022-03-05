<template>
    <g
        :id="elId"
        :class="[{ canClick: canClick }]"
        :transform="`translate(${currentX}, ${currentY}) scale(${scale})`"
        :opacity="transparent ? 0.3 : 1"
        @click="canClick && $emit('click')"
    >
        <path d="M6,4 A6,4,0 0,1 14,4 L14,16 A6,4 0 0,1 6,16Z" fill="none" stroke="black" />
        <path d="M6,4 A6,4 0 0,0 14,4 A6,4 0 0,0 6,4" fill="#556" />
        <path d="M6,4 A6,4 0 0,0 6,4 L6,16 A6,4,0 0,0 14,16 L14,4 A6,4 0 0,1 6,4" fill="url(#oil-linear)" />

        <title>Oil</title>

        <defs>
            <linearGradient id="oil-linear" x1="0" y1="10" x2="20" y2="10" gradientUnits="userSpaceOnUse">
                <stop stop-color="#445" />
                <stop offset="1" stop-color="#223" />
            </linearGradient>
        </defs>
    </g>
</template>
<script lang="ts">
import { PieceType } from './../../types/ui-data';
import { Component, Mixins, Prop } from 'vue-property-decorator';
import Piece from './Piece.vue';

@Component({
    created(this: Oil) {
        this.pieceType = PieceType.Oil;
    }
})
export default class Oil extends Mixins(Piece) {
    @Prop()
    canClick?: boolean;

    @Prop({ default: 1 })
    scale?: number;
}
</script>
