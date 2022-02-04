<template>
    <g
        :id="elId"
        :class="[{ canClick: canClick }]"
        :transform="`translate(${currentX}, ${currentY}) scale(${scale})`"
        :opacity="transparent ? 0.3 : 1"
        @click="canClick && $emit('click')"
    >
        <path
            d="M136.8 21.2L43.1001 48.9L43.2001 167.2L135.2 210.3L228.8 174V55.7L136.8 21.2Z"
            fill="#5a2d0c"
            stroke="black"
            stroke-width="20"
            stroke-miterlimit="10"
        />
        <path d="M135.2 210.3L43.2001 167.2L43.1001 48.8999L135.1 83.4999L135.2 210.3Z" fill="#70380f" />
        <path d="M135.1 83.5L43.1001 48.9L136.8 21.2L228.8 55.7L135.1 83.5Z" fill="#8b4513" />
        <path d="M228.8 55.7V174L135.2 210.3L135.1 83.5L228.8 55.7Z" fill="#5a2d0c" />

        <title>Coal</title>
    </g>
</template>
<script lang="ts">
import { PieceType } from './../../types/ui-data';
import { Component, Mixins, Prop } from 'vue-property-decorator';
import Piece from './Piece.vue';

@Component({
    created(this: Coal) {
        this.pieceType = PieceType.Coal;
    }
})
export default class Coal extends Mixins(Piece) {
    @Prop()
    canClick?: boolean;

    @Prop({ default: 0.08 })
    scale?: number;
}
</script>
