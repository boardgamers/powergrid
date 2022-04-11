<template>
    <g v-if="powerPlant.number == 99" :id="elId" :transform="`translate(${currentX}, ${currentY})`">
        <rect width="60" height="40" :fill="getColor()" stroke="black" stroke-width="2" rx="4" />
        <text text-anchor="middle" x="30" y="20" fill="black">Step 3</text>
    </g>
    <g
        v-else
        :id="elId"
        :class="[{ canClick: canClick }]"
        :transform="`translate(${currentX}, ${currentY})`"
        @click="canClick && $emit('click')"
    >
        <rect
            width="60"
            height="40"
            :fill="getColor()"
            :stroke="hasDiscount ? 'palegreen' : 'black'"
            stroke-width="2"
            rx="4"
        />
        <g v-if="hasDiscount">
            <rect width="12" height="12" rx="4" fill="palegreen" />
            <text text-anchor="middle" x="6" y="6" style="font-size: 12px" fill="black">$</text>
        </g>
        <g transform="translate(30, 10)">
            <text text-anchor="middle" x="1" y="1" fill="gray">{{ powerPlant.number }}</text>
            <text text-anchor="middle" fill="white">{{ powerPlant.number }}</text>
        </g>

        <g :id="elId" :class="['piece']" transform="translate(40, 20) scale(0.035)">
            <path
                d="M187.698 263.636V456.017L3 341.204V169.522L80.8579 108.141L187.698 263.636Z"
                fill="white"
                stroke="white"
                stroke-width="12"
                stroke-miterlimit="10"
            />
            <path
                d="M395.724 136.361V300.164L187.698 456.017V263.636L395.724 136.361Z"
                fill="white"
                stroke="white"
                stroke-width="12"
                stroke-miterlimit="10"
            />
            <path
                d="M395.724 136.361L187.698 263.636L80.8579 108.141L304.771 4L395.724 136.361Z"
                fill="white"
                stroke="white"
                stroke-width="12"
                stroke-miterlimit="10"
            />
        </g>
        <text text-anchor="middle" x="47" y="28" style="font-size: 12px" fill="black">
            {{ powerPlant.citiesPowered }}
        </text>

        <g transform="translate(5, 20)">
            <path :d="getResourcePath()" fill="white" />
        </g>
        <text v-if="powerPlant.cost > 0" text-anchor="middle" x="12.5" y="27.5" style="font-size: 12px" fill="black">
            {{ powerPlant.cost }}
        </text>

        <g transform="translate(24, 22)">
            <path d="M0,3 L8,3 L8,0 L14,6 L8,12 L8,9 L0,9Z" fill="white" />
        </g>

        <defs>
            <linearGradient id="hybrid" x1="0" y1="0" x2="100%" y2="100%">
                <stop offset="50%" stop-color="#8b4513" />
                <stop offset="50%" stop-color="#445" />
            </linearGradient>
        </defs>
    </g>
</template>
<script lang="ts">
import { PieceType } from './../../types/ui-data';
import { PowerPlant, PowerPlantType } from 'powergrid-engine/src/gamestate';
import { Component, Mixins, Prop } from 'vue-property-decorator';
import Piece from './Piece.vue';

@Component({
    created(this: Card) {
        this.pieceType = PieceType.Card;
    }
})
export default class Card extends Mixins(Piece) {
    @Prop()
    owner?: number;

    @Prop()
    powerPlant?: PowerPlant;

    @Prop()
    canClick?: boolean;

    @Prop({ default: false })
    hasDiscount?: boolean;

    getColor() {
        switch (this.powerPlant?.type) {
            case PowerPlantType.Coal: return '#8b4513';
            case PowerPlantType.Oil: return '#445';
            case PowerPlantType.Garbage: return 'goldenrod';
            case PowerPlantType.Uranium: return 'red';
            case PowerPlantType.Hybrid: return 'url(#hybrid)';
            case PowerPlantType.Wind: return 'limegreen';
            case PowerPlantType.Nuclear: return 'dodgerblue';
            case PowerPlantType.Step3: return 'dodgerblue';
        }
    }

    getResourcePath() {
        switch (this.powerPlant?.type) {
            case PowerPlantType.Coal: return 'M0,3 L7.5,0 L15,3 L15,12 L7.5,15 L0,12Z';
            case PowerPlantType.Oil: return 'M3,2 A6,3 0 0,1 12,2 L12,12 A6,3 0 0,1 3,12Z';
            case PowerPlantType.Garbage: return 'M0,3 A7.5,3 0 0,1 15,3 L15,12 A7.5,3 0 0,1 0,12Z';
            case PowerPlantType.Uranium: return 'M1,2 l4,-2 l6,0 l4,2 l0,11 l-4,2 l-6,0 l-4,-2Z';
            case PowerPlantType.Hybrid: return 'M0,3 L7.5,0 L15,3 L15,12 L7.5,15 L0,12Z M9,1 A6,3 0 0,1 18,1 L18,10 A6,3 0 0,1 10,10Z';
            case PowerPlantType.Wind: return '';
            case PowerPlantType.Nuclear: return '';
            case PowerPlantType.Step3: return '';
        }
    }
}
</script>
<style lang="scss">
.canClick {
    cursor: pointer;
}
</style>
