<template>
    <g :id="elId" :class="['piece', { dragging, canDrag }]" :transform="`translate(${currentX}, ${currentY})`">
        <path d="M15 0 L30 10 L30 30 L0 30 L0 10Z" fill="dimgray" stroke="black" />
        <title>Warehouse</title>
    </g>
</template>
<script lang="ts">
import { PieceType } from '@/types/ui-data';
import { Component, Mixins } from 'vue-property-decorator';
import Piece from './Piece.vue';

@Component({
    created(this: Warehouse) {
        this.pieceType = PieceType.Warehouse;
    }
})
export default class Warehouse extends Mixins(Piece) {
}
</script>
