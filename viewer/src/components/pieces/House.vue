<template>
    <g :id="elId" :class="['piece']" :transform="`translate(${currentX}, ${currentY}) scale(${scale})`">
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
        <g v-if="preferences.colorBlind && owner !== undefined" class="house-owner" pointer-events="none">
            <circle cx="200" cy="285" r="143" fill="#fffbe9" stroke="#17251d" stroke-width="18" />
            <text
                x="200"
                y="288"
                text-anchor="middle"
                dominant-baseline="central"
                style="font: bold 255px sans-serif; fill: #17251d"
                >{{ owner + 1 }}</text
            >
        </g>
        <title>{{ houseTitle }}</title>
    </g>
</template>
<script lang="ts">
import { PieceType, Preferences } from './../../types/ui-data';
import { Component, Inject, InjectReactive, Mixins, Prop } from 'vue-property-decorator';
import Piece from './Piece.vue';

@Component({
    created(this: House) {
        this.pieceType = PieceType.House;
    }
})
export default class House extends Mixins(Piece) {
    @Inject() readonly preferences!: Preferences;

    @InjectReactive()
    readonly player!: number;

    @Prop()
    color?: string;

    @Prop({ default: 0.035 })
    scale!: number;

    @Prop()
    owner?: number;

    @Prop()
    ownerName?: string;

    get houseTitle() {
        if (this.owner !== undefined && this.owner === this.player) return 'Your House';
        if (this.ownerName) return `${this.ownerName}'s House`;
        return this.owner === undefined ? 'House' : `Player ${this.owner + 1}'s House`;
    }
}
</script>
