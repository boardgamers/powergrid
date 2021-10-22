<template>
    <g :id="elId" :class="['piece']" :transform="`translate(${currentX}, ${currentY})`">
        <g transform="scale(0.08)">
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
        </g>

        <g transform="translate(5, 0)">
            <path d="M6,4 A6,4,0 0,1 14,4 L14,16 A6,4 0 0,1 6,16Z" fill="none" stroke="black" />
            <path d="M6,4 A6,4 0 0,0 14,4 A6,4 0 0,0 6,4" fill="#556" />
            <path d="M6,4 A6,4 0 0,0 6,4 L6,16 A6,4,0 0,0 14,16 L14,4 A6,4 0 0,1 6,4" fill="url(#oil-linear)" />
        </g>

        <title>Coal/Oil</title>
    </g>
</template>
<script lang="ts">
import { PieceType } from '@/types/ui-data';
import { Component, Mixins } from 'vue-property-decorator';
import Piece from './Piece.vue';
import { Coal, Oil } from '.';

@Component({
    created(this: Hybrid) {
        this.pieceType = PieceType.Hybrid;
    },
    components: {
        Coal, Oil
    },
})
export default class Hybrid extends Mixins(Piece) {
}
</script>
