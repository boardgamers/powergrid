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
        <!-- Christmas, Dec 1 - Jan 6: snow on the roof (inset, so a rim of the player's
             colour still shows) and a string of lights along the roofline. Drawn under
             the colour-blind symbol, which must always stay readable. -->
        <g v-if="holiday !== 'none'" :class="['house-holiday', holiday]" data-holiday="christmas" pointer-events="none">
            <path
                d="M395.724 136.361L187.698 263.636L80.8579 108.141L304.771 4L395.724 136.361Z"
                fill="#fbfdff"
                stroke="#d7e3ec"
                stroke-width="4"
                transform="translate(242 128) scale(0.8) translate(-242 -128)"
            />
            <polyline :points="rooflinePoints" fill="none" stroke="#24352a" stroke-width="5" stroke-linejoin="round" />
            <circle
                v-for="(bulb, i) in bulbs"
                :key="i"
                :cx="bulb.x"
                :cy="bulb.y"
                r="18"
                :fill="bulb.color"
                stroke="#1b2a20"
                stroke-width="3"
                :class="['bulb', { alternate: bulb.alternate }]"
            />
        </g>
        <g v-if="preferences.colorBlind && owner !== undefined" class="house-owner" pointer-events="none">
            <path
                v-if="ownerSymbolPath"
                :d="ownerSymbolPath"
                transform="translate(-40, -5) scale(20)"
                fill="#17251d"
                stroke="white"
                stroke-width="1.4"
                stroke-linejoin="round"
                paint-order="stroke fill"
            />
            <text
                v-else
                x="200"
                y="235"
                text-anchor="middle"
                dominant-baseline="central"
                stroke="white"
                stroke-width="18"
                stroke-linejoin="round"
                paint-order="stroke fill"
                style="font: bold 480px sans-serif; fill: #17251d"
                >{{ ownerSymbol }}</text
            >
        </g>
        <title>{{ houseTitle }}</title>
    </g>
</template>
<script lang="ts">
import { playerSymbol } from '../../player-colors';
import { BULBS, holidayLook, ROOFLINE_POINTS } from '../../util/holiday';
import { isPlayerSymbol, PLAYER_SYMBOLS } from '@boardgamers/protocol/player-symbols';
import { PieceType, Preferences } from './../../types/ui-data';
import { Component, Inject, InjectReactive, Mixins, Prop } from 'vue-property-decorator';
import Piece from './Piece.vue';

@Component({
    created(this: House) {
        this.pieceType = PieceType.House;
    },
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

    readonly bulbs = BULBS;
    readonly rooflinePoints = ROOFLINE_POINTS;

    get holiday() {
        return holidayLook(this.preferences);
    }

    get ownerSymbol() {
        return playerSymbol(this.owner!, this.preferences);
    }

    get ownerSymbolPath() {
        const symbol = this.preferences.bgs?.playerSymbols?.[this.owner!];
        return isPlayerSymbol(symbol) ? PLAYER_SYMBOLS[symbol].path : undefined;
    }

    get houseTitle() {
        if (this.owner !== undefined && this.owner === this.player) return 'Your House';
        if (this.ownerName) return `${this.ownerName}'s House`;
        return this.owner === undefined ? 'House' : `Player ${this.owner + 1}'s House`;
    }
}
</script>

<style>
.house-holiday.lively .bulb {
    animation: house-bulb-blink 1.6s steps(1, end) infinite;
}

.house-holiday.lively .bulb.alternate {
    animation-delay: 0.8s;
}

@keyframes house-bulb-blink {
    0% {
        opacity: 1;
    }
    50% {
        opacity: 0.3;
    }
}

@media (prefers-reduced-motion: reduce) {
    .house-holiday .bulb {
        animation: none !important;
    }
}
</style>
