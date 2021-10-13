<template>
    <g :id="elId" :class="['piece', { dragging, canDrag }]" :transform="`translate(${currentX}, ${currentY})`">
        <circle r="10" :fill="color" stroke="black" />

        <title>Factory</title>
    </g>
</template>
<script lang="ts">
import { PieceType } from '@/types/ui-data';
import { Component, Mixins, Prop } from 'vue-property-decorator';
import Piece from './Piece.vue';

@Component({
    created(this: Factory) {
        this.pieceType = PieceType.Factory;
    }
})
export default class Factory extends Mixins(Piece) {
    @Prop()
    color?: string;
}
</script>
