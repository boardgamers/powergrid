<template>
    <g>
        <text x="30" y="20" font-weight="600" fill="black" style="font-size: 24px">Resource Resupply:</text>
        <text x="276" y="20" font-weight="600" fill="black" style="font-size: 24px">
            {{ resourceResupply[0] }}
        </text>
        <Coal :pieceId="-1" :targetState="{ x: 288, y: 12 }" :canClick="false" :transparent="false" />
        <text x="321" y="20" font-weight="600" fill="black" style="font-size: 24px">
            {{ resourceResupply[1] }}
        </text>
        <Oil :pieceId="-1" :targetState="{ x: 331, y: 11 }" :canClick="false" :transparent="false" />
        <text x="368" y="20" font-weight="600" fill="black" style="font-size: 24px">
            {{ resourceResupply[2] }}
        </text>
        <Garbage :pieceId="-1" :targetState="{ x: 382, y: 11 }" :canClick="false" :transparent="false" />
        <text x="414" y="20" font-weight="600" fill="black" style="font-size: 24px">
            {{ resourceResupply[3] }}
        </text>
        <Uranium :pieceId="-1" :targetState="{ x: 428, y: 12 }" :canClick="false" :transparent="false" />

        <rect width="760" height="80" x="20" y="40" rx="3" fill="goldenrod" />
        <template v-for="index in 8">
            <rect
                :key="'resources' + index"
                width="70"
                height="70"
                :x="25 + 85 * (index - 1)"
                y="45"
                rx="2"
                fill="darkgoldenrod"
            />
            <circle :key="'resourcesCircle' + index" r="10" :cx="92 + 85 * (index - 1)" cy="48" fill="yellow" />
            <text
                :key="'resourcesText' + index"
                text-anchor="middle"
                style="font-size: 16px; font-family: monospace"
                :x="92 + 85 * (index - 1)"
                y="48"
                fill="darkgoldenrod"
            >
                {{ index }}
            </text>
            <g :key="'lines' + index">
                <line :x1="25 + 85 * (index - 1)" y1="68" :x2="95 + 85 * (index - 1)" y2="68" stroke="goldenrod" />
                <line :x1="25 + 85 * (index - 1)" y1="92" :x2="95 + 85 * (index - 1)" y2="92" stroke="goldenrod" />

                <line :x1="48 + 85 * (index - 1)" y1="40" :x2="48 + 85 * (index - 1)" y2="68" stroke="goldenrod" />
                <line :x1="72 + 85 * (index - 1)" y1="40" :x2="72 + 85 * (index - 1)" y2="68" stroke="goldenrod" />
                <line :x1="42 + 85 * (index - 1)" y1="68" :x2="42 + 85 * (index - 1)" y2="92" stroke="goldenrod" />
                <line :x1="58 + 85 * (index - 1)" y1="68" :x2="58 + 85 * (index - 1)" y2="92" stroke="goldenrod" />
                <line :x1="74 + 85 * (index - 1)" y1="68" :x2="74 + 85 * (index - 1)" y2="92" stroke="goldenrod" />
                <line :x1="48 + 85 * (index - 1)" y1="92" :x2="48 + 85 * (index - 1)" y2="120" stroke="goldenrod" />
                <line :x1="72 + 85 * (index - 1)" y1="92" :x2="72 + 85 * (index - 1)" y2="120" stroke="goldenrod" />
            </g>
        </template>

        <rect width="30" height="30" x="705" y="45" rx="2" fill="darkgoldenrod" />
        <circle r="10" cx="732" cy="48" fill="yellow" />
        <text text-anchor="middle" style="font-size: 12px; font-family: monospace" x="732" y="48" fill="darkgoldenrod">
            10
        </text>

        <rect width="30" height="30" x="745" y="45" rx="2" fill="darkgoldenrod" />
        <circle r="10" cx="772" cy="48" fill="yellow" />
        <text text-anchor="middle" style="font-size: 12px; font-family: monospace" x="772" y="48" fill="darkgoldenrod">
            12
        </text>

        <rect width="30" height="30" x="705" y="85" rx="2" fill="darkgoldenrod" />
        <circle r="10" cx="732" cy="88" fill="yellow" />
        <text text-anchor="middle" style="font-size: 12px; font-family: monospace" x="732" y="88" fill="darkgoldenrod">
            14
        </text>

        <rect width="30" height="30" x="745" y="85" rx="2" fill="darkgoldenrod" />
        <circle r="10" cx="772" cy="88" fill="yellow" />
        <text text-anchor="middle" style="font-size: 12px; font-family: monospace" x="772" y="88" fill="darkgoldenrod">
            16
        </text>

        <template v-for="coal in coals">
            <Coal
                :key="coal.id"
                :pieceId="coal.id"
                :targetState="{ x: coal.x, y: coal.y }"
                :canClick="!coal.transparent && canBuyResource('coal')"
                :transparent="coal.transparent"
                @click="buyResource('coal')"
            />
        </template>

        <template v-for="oil in oils">
            <Oil
                :key="oil.id"
                :pieceId="oil.id"
                :targetState="{ x: oil.x, y: oil.y }"
                :canClick="!oil.transparent && canBuyResource('oil')"
                :transparent="oil.transparent"
                @click="buyResource('oil')"
            />
        </template>

        <template v-for="garbage in garbages">
            <Garbage
                :key="garbage.id"
                :pieceId="garbage.id"
                :targetState="{ x: garbage.x, y: garbage.y }"
                :canClick="!garbage.transparent && canBuyResource('garbage')"
                :transparent="garbage.transparent"
                @click="buyResource('garbage')"
            />
        </template>

        <template v-for="uranium in uraniums">
            <Uranium
                :key="uranium.id"
                :pieceId="uranium.id"
                :targetState="{ x: uranium.x, y: uranium.y }"
                :canClick="!uranium.transparent && canBuyResource('uranium')"
                :transparent="uranium.transparent"
                @click="buyResource('uranium')"
            />
        </template>

        <template v-if="isUsaRecharged">
            <rect
                width="180"
                height="70"
                x="795"
                y="45"
                rx="2"
                fill="chocolate"
                stroke="sandybrown"
                stroke-width="4px"
            />
            <circle r="10" cx="973" cy="45" fill="yellow" />
            <text
                text-anchor="middle"
                style="font-size: 16px; font-family: monospace"
                x="973"
                y="45"
                fill="darkgoldenrod"
            >
                8
            </text>
            <Coal :pieceId="-1" :targetState="{ x: 858, y: 57 }" :canClick="false" :transparent="true" :scale="0.2" />
        </template>

        <template v-if="isMiddleEast">
            <rect width="80" height="50" x="20" y="70" rx="2" fill="gray" stroke="darkgray" stroke-width="4px" />
            <Oil
                :pieceId="-1"
                :targetState="{ x: 35, y: 80, scale: 1.5 }"
                :canClick="availableSurplusOil > 0"
                :transparent="availableSurplusOil == 0"
                @click="buyResource('oil')"
            />
            <text text-anchor="middle" style="font-size: 16px; font-family: monospace" x="70" y="93.5">
                x{{ availableSurplusOil }}
            </text>
        </template>

        <template v-if="!preferences.disableHelp">
            <rect
                v-if="buyableResources.length > 0"
                x="15"
                y="35"
                width="770"
                height="90"
                rx="2"
                fill="none"
                stroke="blue"
                stroke-width="2px"
            />
        </template>
    </g>
</template>

<script lang="ts">
import type { GameState } from 'powergrid-engine';
import { Vue, Component, Prop, Inject } from 'vue-property-decorator';
import { Coal, Garbage, Oil, Uranium } from '../pieces';
import { Piece, Preferences } from '../../types/ui-data';
import { range } from 'lodash';

@Component({
    components: {
        Coal, Oil, Garbage, Uranium
    },
})
export default class Resources extends Vue {
    @Prop() resourceResupply?: number[];
    @Prop() isUsaRecharged?: boolean;
    @Prop() isMiddleEast?: boolean;
    @Prop() availableSurplusOil?: number;
    @Prop() buyableResources?: string[];

    @Inject() preferences!: Preferences;

    coals: Piece[] = [];
    oils: Piece[] = [];
    garbages: Piece[] = [];
    uraniums: Piece[] = [];

    createPieces(gameState: GameState) {
        if (gameState) {
            this.coals = [];
            Array(24)
                .fill(0)
                .forEach((_, i) => {
                    this.coals.push({
                        id: 'coal_' + i,
                        x: 668 - 23.5 * i - 14.5 * Math.floor(i / 3),
                        y: 48,
                        transparent: i >= gameState!.coalMarket,
                    });
                });

            if (gameState.options.variant == 'recharged' && gameState.map.name == 'USA') {
                range(gameState.coalSupply).forEach((i) => {
                    this.coals.push({
                        id: 'coal_supply_' + i,
                        x: 800 + (i % 8) * 20 + (i >= 8 && i < 16 ? 10 : 0),
                        y: 50 + Math.floor(i / 8) * 20,
                        transparent: false,
                    });
                });
            }

            this.oils = [];
            if (gameState.map.name == 'Middle East') {
                let maxRegularOil = gameState.oilPrices.filter(p => p > 1).length;
                let maxSurplusOil = gameState.oilPrices.filter(p => p == 1).length;
                let availableRegularOil = Math.min(maxRegularOil, gameState.oilMarket);

                Array(maxRegularOil)
                    .fill(0)
                    .forEach((_, i) => {
                        let adjustedIndex = i + (maxSurplusOil - 3);
                        console.log('Oil index', adjustedIndex);
                        this.oils.push({
                            id: 'normal_oil_' + adjustedIndex,
                            x: 651 - 16 * adjustedIndex - 37 * Math.floor(adjustedIndex / 3),
                            y: 70,
                            transparent: i >= availableRegularOil,
                        });
                    });
            } else {
                Array(24)
                    .fill(0)
                    .forEach((_, i) => {
                        this.oils.push({
                            id: 'oil_' + i,
                            x: 651 - 16 * i - 37 * Math.floor(i / 3),
                            y: 70,
                            transparent: i >= gameState!.oilMarket,
                        });
                    });
            }

            this.garbages = [];
            Array(24)
                .fill(0)
                .forEach((_, i) => {
                    this.garbages.push({
                        id: 'garbage_' + i,
                        x: 668 - 23.5 * i - 14.5 * Math.floor(i / 3),
                        y: 94,
                        transparent: i >= gameState!.garbageMarket,
                    });
                });

            this.uraniums = [];
            Array(12)
                .fill(0)
                .forEach((_, i) => {
                    if (i == 0) {
                        this.uraniums.push({
                            id: 'uranium_' + i,
                            x: 750,
                            y: 91,
                            transparent: i >= gameState!.uraniumMarket,
                        });
                    } else if (i == 1) {
                        this.uraniums.push({
                            id: 'uranium_' + i,
                            x: 710,
                            y: 91,
                            transparent: i >= gameState!.uraniumMarket,
                        });
                    } else if (i == 2) {
                        this.uraniums.push({
                            id: 'uranium_' + i,
                            x: 750,
                            y: 52,
                            transparent: i >= gameState!.uraniumMarket,
                        });
                    } else if (i == 3) {
                        this.uraniums.push({
                            id: 'uranium_' + i,
                            x: 710,
                            y: 52,
                            transparent: i >= gameState!.uraniumMarket,
                        });
                    } else {
                        this.uraniums.push({
                            id: 'uranium_' + i,
                            x: 1010 - 85 * i,
                            y: 72,
                            transparent: i >= gameState!.uraniumMarket,
                        });
                    }
                });
        }
    }

    canBuyResource(resource: string) {
        return !!this.buyableResources!.find(r => r == resource);
    }

    buyResource(resource: string) {
        this.$emit('buyResource', resource);
    }
}
</script>
