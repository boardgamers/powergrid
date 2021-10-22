<template>
    <g
        :id="elId"
        :class="[{ canClick: canClick }]"
        :transform="`translate(${currentX}, ${currentY})`"
        :opacity="transparent ? 0.3 : 1"
        @click="canClick && $emit('click')"
    >
        <path d="M3,3 l4,-2 l6,0 l4,2 l0,11 l-4,2 l-6,0 l-4,-2Z" fill="none" stroke="black" />
        <path d="M3,3 l4,-2 l6,0 l4,2 l0,2 l-4,2 l-6,0 l-4,-2 l0,-2" fill="#F00" />
        <path d="M3,5 l0,9 l4,2 l0,-9 l-4,-2" fill="#e60000" />
        <path d="M7,7 l6,0 l0,9 l-6,0 l0,-9" fill="#cc0000" />
        <path d="M13,7 l4,-2 l0,9 l-4,2 l0,-9" fill="#b30000" />

        <title>Uranium</title>
    </g>
</template>
<script lang="ts">
import { PieceType } from '@/types/ui-data';
import { Component, Mixins, Prop } from 'vue-property-decorator';
import Piece from './Piece.vue';

@Component({
    created(this: Uranium) {
        this.pieceType = PieceType.Uranium;
    }
})
export default class Uranium extends Mixins(Piece) {
    @Prop()
    canClick?: boolean;
}
</script>
