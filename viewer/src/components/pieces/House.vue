<template>
    <g :id="elId" :class="['piece']" :transform="`translate(${currentX}, ${currentY}) scale(0.035)`">
        <!-- <path d="M15 0 L30 10 L30 30 L0 30 L0 10Z" :fill="color" stroke="black" /> -->
        <path
            d="M187.698 263.636V456.017L3 341.204V169.522L80.8579 108.141L187.698 263.636Z"
            :fill="color"
            stroke="#010101"
            stroke-width="12"
            stroke-miterlimit="10"
        />
        <path
            d="M395.724 136.361V300.164L187.698 456.017V263.636L395.724 136.361Z"
            :fill="color"
            stroke="#010101"
            stroke-width="12"
            stroke-miterlimit="10"
        />
        <path
            d="M395.724 136.361L187.698 263.636L80.8579 108.141L304.771 4L395.724 136.361Z"
            :fill="color"
            stroke="#010101"
            stroke-width="12"
            stroke-miterlimit="10"
        />
        <title>{{ ownerName }}'s House</title>
    </g>
</template>
<script lang="ts">
import { PieceType } from './../../types/ui-data';
import { Component, InjectReactive, Mixins, Prop } from 'vue-property-decorator';
import Piece from './Piece.vue';

@Component({
    created(this: House) {
        this.pieceType = PieceType.House;
    }
})
export default class House extends Mixins(Piece) {
    @InjectReactive()
    readonly player!: number;

    @Prop()
    color?: string;

    @Prop()
    owner?: number;

    @Prop()
    ownerName?: string;
}
</script>
