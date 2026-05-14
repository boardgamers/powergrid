<template>
    <g>
        <!-- Korea: North resource market (above the standard market block).
             The South market re-uses the existing rendering below; Korea-specific
             cube positions are populated in createPieces. -->
        <template v-if="isKorea">
            <text x="20" y="-110" font-weight="700" fill="black" style="font-size: 22px">North Market</text>
            <rect width="760" height="80" x="20" y="-100" rx="3" fill="#c89c3a" />
            <template v-for="index in 8">
                <rect
                    :key="'north_resources' + index"
                    width="70"
                    height="70"
                    :x="25 + 85 * (index - 1)"
                    y="-95"
                    rx="2"
                    fill="darkgoldenrod"
                />
                <circle
                    :key="'north_resourcesCircle' + index"
                    r="10"
                    :cx="92 + 85 * (index - 1)"
                    cy="-92"
                    fill="yellow"
                />
                <text
                    :key="'north_resourcesText' + index"
                    text-anchor="middle"
                    style="font-size: 16px; font-family: monospace"
                    :x="92 + 85 * (index - 1)"
                    y="-92"
                    fill="darkgoldenrod"
                >
                    {{ index }}
                </text>
            </template>
            <template v-for="coal in coalsNorth">
                <Coal
                    :key="coal.id"
                    :pieceId="coal.id"
                    :targetState="{ x: coal.x, y: coal.y }"
                    :canClick="!coal.transparent && canBuyResource('coal', coal.side, coal.fromStorage)"
                    :transparent="coal.transparent"
                    :scale="0.08"
                    @click="buyResource('coal', coal.side, coal.fromStorage)"
                />
            </template>
            <template v-for="oil in oilsNorth">
                <Oil
                    :key="oil.id"
                    :pieceId="oil.id"
                    :targetState="{ x: oil.x, y: oil.y }"
                    :canClick="!oil.transparent && canBuyResource('oil', oil.side)"
                    :transparent="oil.transparent"
                    @click="buyResource('oil', oil.side)"
                />
            </template>
            <template v-for="garbage in garbagesNorth">
                <Garbage
                    :key="garbage.id"
                    :pieceId="garbage.id"
                    :targetState="{ x: garbage.x, y: garbage.y }"
                    :canClick="!garbage.transparent && canBuyResource('garbage', garbage.side)"
                    :transparent="garbage.transparent"
                    @click="buyResource('garbage', garbage.side)"
                />
            </template>
            <text x="20" y="35" font-weight="700" fill="black" style="font-size: 22px">South Market</text>
        </template>

        <text v-if="resourceResupply[0] < 10" x="30" y="20" font-weight="600" fill="black" style="font-size: 24px"
            >Resource Resupply:</text
        >
        <text v-else x="20" y="20" font-weight="600" fill="black" style="font-size: 24px">Resource Resupply:</text>
        <text v-if="resourceResupply[0] < 10" x="276" y="20" font-weight="600" fill="black" style="font-size: 24px">
            {{ resourceResupply[0] }}
        </text>
        <text v-else x="262" y="20" font-weight="600" fill="black" style="font-size: 24px">
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

        <rect
            v-if="!isIndiaResourceMarket && !isNinePriceMarket"
            width="760"
            height="80"
            x="20"
            y="40"
            rx="3"
            fill="goldenrod"
        />
        <rect v-if="isNinePriceMarket" width="780" height="80" x="20" y="40" rx="3" fill="goldenrod" />
        <rect v-if="isIndiaResourceMarket" width="680" height="80" x="20" y="40" rx="3" fill="goldenrod" />
        <template v-for="index in isNinePriceMarket ? 9 : 8">
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
            <g :key="'lines' + index" v-if="!isIndiaResourceMarket && !isNinePriceMarket">
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
            <g :key="'lines' + index" v-if="isIndiaResourceMarket">
                <line :x1="25 + 85 * (index - 1)" y1="68" :x2="95 + 85 * (index - 1)" y2="68" stroke="goldenrod" />
                <line :x1="25 + 85 * (index - 1)" y1="92" :x2="95 + 85 * (index - 1)" y2="92" stroke="goldenrod" />

                <line :x1="42 + 85 * (index - 1)" y1="40" :x2="42 + 85 * (index - 1)" y2="68" stroke="goldenrod" />
                <line :x1="59 + 85 * (index - 1)" y1="40" :x2="59 + 85 * (index - 1)" y2="68" stroke="goldenrod" />
                <line :x1="76 + 85 * (index - 1)" y1="40" :x2="76 + 85 * (index - 1)" y2="68" stroke="goldenrod" />
                <line :x1="42 + 85 * (index - 1)" y1="68" :x2="42 + 85 * (index - 1)" y2="92" stroke="goldenrod" />
                <line :x1="58 + 85 * (index - 1)" y1="68" :x2="58 + 85 * (index - 1)" y2="92" stroke="goldenrod" />
                <line :x1="74 + 85 * (index - 1)" y1="68" :x2="74 + 85 * (index - 1)" y2="92" stroke="goldenrod" />
                <line :x1="42 + 85 * (index - 1)" y1="92" :x2="42 + 85 * (index - 1)" y2="120" stroke="goldenrod" />
                <line :x1="59 + 85 * (index - 1)" y1="92" :x2="59 + 85 * (index - 1)" y2="120" stroke="goldenrod" />
                <line :x1="76 + 85 * (index - 1)" y1="92" :x2="76 + 85 * (index - 1)" y2="120" stroke="goldenrod" />
            </g>
        </template>

        <template v-if="isIndiaResourceMarket">
            <g :key="'separators'">
                <line x1="275" y1="40" x2="275" y2="140" stroke="red" />
                <line x1="445" y1="40" x2="445" y2="140" stroke="red" />

                <text x="220" y="130" stroke="red">Step 1</text>
                <text x="390" y="130" stroke="red">Step 2</text>
            </g>
        </template>

        <template v-if="!isIndiaResourceMarket && !isNinePriceMarket">
            <rect width="30" height="30" x="705" y="45" rx="2" fill="darkgoldenrod" />
            <circle r="10" cx="732" cy="48" fill="yellow" />
            <text
                text-anchor="middle"
                style="font-size: 12px; font-family: monospace"
                x="732"
                y="48"
                fill="darkgoldenrod"
            >
                10
            </text>

            <rect width="30" height="30" x="745" y="45" rx="2" fill="darkgoldenrod" />
            <circle r="10" cx="772" cy="48" fill="yellow" />
            <text
                text-anchor="middle"
                style="font-size: 12px; font-family: monospace"
                x="772"
                y="48"
                fill="darkgoldenrod"
            >
                12
            </text>

            <rect width="30" height="30" x="705" y="85" rx="2" fill="darkgoldenrod" />
            <circle r="10" cx="732" cy="88" fill="yellow" />
            <text
                text-anchor="middle"
                style="font-size: 12px; font-family: monospace"
                x="732"
                y="88"
                fill="darkgoldenrod"
            >
                14
            </text>

            <rect width="30" height="30" x="745" y="85" rx="2" fill="darkgoldenrod" />
            <circle r="10" cx="772" cy="88" fill="yellow" />
            <text
                text-anchor="middle"
                style="font-size: 12px; font-family: monospace"
                x="772"
                y="88"
                fill="darkgoldenrod"
            >
                16
            </text>
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

        <!-- South Africa: coal storage pool below the market. Always-available $8
             flat buy. Used coal returns here; market refills draw from here first. -->
        <template v-if="coalStorage !== undefined">
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
            <text text-anchor="start" style="font-size: 11px; font-family: monospace" x="800" y="42" fill="black">
                Coal storage
            </text>
        </template>

        <template v-for="coal in coals">
            <Coal
                :key="coal.id"
                :pieceId="coal.id"
                :targetState="{ x: coal.x, y: coal.y }"
                :canClick="!coal.transparent && canBuyResource('coal', coal.side, coal.fromStorage)"
                :transparent="coal.transparent"
                :scale="isIndiaResourceMarket ? 0.06 : 0.08"
                @click="buyResource('coal', coal.side, coal.fromStorage)"
            />
        </template>

        <template v-for="oil in oils">
            <Oil
                :key="oil.id"
                :pieceId="oil.id"
                :targetState="{ x: oil.x, y: oil.y }"
                :canClick="!oil.transparent && canBuyResource('oil', oil.side)"
                :transparent="oil.transparent"
                @click="buyResource('oil', oil.side)"
            />
        </template>

        <template v-for="garbage in garbages">
            <Garbage
                :key="garbage.id"
                :pieceId="garbage.id"
                :targetState="{ x: garbage.x, y: garbage.y }"
                :canClick="!garbage.transparent && canBuyResource('garbage', garbage.side)"
                :transparent="garbage.transparent"
                :scale="isIndiaResourceMarket ? 0.8 : 1"
                @click="buyResource('garbage', garbage.side)"
            />
        </template>

        <template v-for="uranium in uraniums">
            <Uranium
                :key="uranium.id"
                :pieceId="uranium.id"
                :targetState="{ x: uranium.x, y: uranium.y }"
                :canClick="!uranium.transparent && canBuyResource('uranium', uranium.side)"
                :transparent="uranium.transparent"
                @click="buyResource('uranium', uranium.side)"
            />
        </template>

        <template v-if="isMiddleEast">
            <rect width="80" height="50" x="20" y="70" rx="2" fill="gray" stroke="darkgray" stroke-width="4px" />
            <Oil
                :pieceId="-1"
                :targetState="{ x: 35, y: 80 }"
                :scale="1.5"
                :canClick="availableSurplusOil > 0 && canBuyResource('oil')"
                :transparent="availableSurplusOil == 0"
                @click="buyResource('oil')"
            />
            <text text-anchor="middle" style="font-size: 16px; font-family: monospace" x="70" y="93.5">
                x{{ availableSurplusOil }}
            </text>
        </template>

        <template v-if="!preferences.disableHelp">
            <rect
                v-if="!isKorea && buyableResources.length > 0"
                x="15"
                y="35"
                width="770"
                height="90"
                rx="2"
                fill="none"
                stroke="blue"
                stroke-width="2px"
            />
            <rect
                v-if="isKorea && hasBuyableNorth"
                x="15"
                y="-105"
                width="770"
                height="90"
                rx="2"
                fill="none"
                stroke="blue"
                stroke-width="2px"
            />
            <rect
                v-if="isKorea && hasBuyableSouth"
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
    @Prop() isIndiaResourceMarket?: boolean;
    @Prop() availableSurplusOil?: number;
    @Prop() buyableResources?: { resource: string, side?: 'north' | 'south', fromStorage?: boolean }[];
    // South Africa: number of coal cubes in the storage pool below the market.
    // Undefined on all other maps (panel is hidden).
    @Prop() coalStorage?: number;

    @Inject() preferences!: Preferences;

    coals: Piece[] = [];
    oils: Piece[] = [];
    garbages: Piece[] = [];
    uraniums: Piece[] = [];

    isKorea: boolean = false;
    isNinePriceMarket: boolean = false;
    coalsNorth: Piece[] = [];
    oilsNorth: Piece[] = [];
    garbagesNorth: Piece[] = [];

    // Lay out cubes within price spaces ($1..$maxPrice) using the prices array
    // to determine slot count per space. Cubes are indexed cheap→expensive in the
    // prices array, so the cheap end empties as the market depletes.
    // Skips entries with price > maxPrice — used for Korea uranium corners ($10..$16),
    // which the caller renders separately. Europe maxPrice=9 (no corners).
    private buildMainRowPieces(
        prices: number[],
        market: number,
        idPrefix: string,
        y: number,
        options: { side?: 'north' | 'south'; maxPrice?: number } = {},
    ): Piece[] {
        const maxPrice = options.maxPrice ?? 8;
        const groups: { price: number; slots: number; firstIdx: number }[] = [];
        prices.forEach((p, idx) => {
            if (p > maxPrice) return;
            const last = groups[groups.length - 1];
            if (last && last.price === p) last.slots++;
            else groups.push({ price: p, slots: 1, firstIdx: idx });
        });

        const pieces: Piece[] = [];
        // Width within a price space across which cubes are distributed. Bigger
        // value → cubes within the same price space appear farther apart.
        const cubeAreaW = 64;
        groups.forEach((g) => {
            const psCenter = 60 + 85 * (g.price - 1);
            for (let s = 0; s < g.slots; s++) {
                const i = g.firstIdx + s;
                const x = g.slots === 1
                    ? psCenter
                    : psCenter - cubeAreaW / 2 + (cubeAreaW * (s + 0.5)) / g.slots;
                pieces.push({
                    id: `${idPrefix}_${i}`,
                    x,
                    y,
                    transparent: i < (prices.length - market),
                    side: options.side,
                });
            }
        });
        return pieces;
    }

    createPieces(gameState: GameState) {
        if (!gameState) return;

        const isKorea = gameState.coalMarketNorth !== undefined;
        this.isKorea = isKorea;

        if (isKorea) {
            // SOUTH market — main row coal/oil/garbage at the existing y positions.
            this.coals = this.buildMainRowPieces(
                gameState.coalPrices!, gameState.coalMarket, 'coal', 48, { side: 'south' },
            );
            this.oils = this.buildMainRowPieces(
                gameState.oilPrices!, gameState.oilMarket, 'oil', 70, { side: 'south' },
            );
            this.garbages = this.buildMainRowPieces(
                gameState.garbagePrices!, gameState.garbageMarket, 'garbage', 94, { side: 'south' },
            );

            // SOUTH uranium: $1..$8 sit between the oil (y=70) and garbage (y=94) rows
            // so they don't visually overlap with oil. $10/$12/$14/$16 go in the corner
            // 2x2 grid (top row at y=52, bottom row at y=91).
            this.uraniums = [];
            const uPrices = gameState.uraniumPrices!;
            uPrices.forEach((p, i) => {
                let x: number, y: number;
                if (p <= 8) {
                    x = 60 + 85 * (p - 1);
                    y = 85;
                } else {
                    // $10 → (710, 52), $12 → (750, 52), $14 → (710, 91), $16 → (750, 91)
                    const cornerX = (p === 10 || p === 14) ? 710 : 750;
                    const cornerY = (p === 10 || p === 12) ? 52 : 91;
                    x = cornerX;
                    y = cornerY;
                }
                this.uraniums.push({
                    id: `uranium_${i}`,
                    x, y,
                    transparent: i < (uPrices.length - gameState.uraniumMarket),
                    side: 'south',
                });
            });

            // NORTH market — placed above the South so its rect sits at y=-100..-20.
            // Cube rows match the South layout's offsets within the rect (top/mid/bottom).
            this.coalsNorth = this.buildMainRowPieces(
                gameState.coalPricesNorth!, gameState.coalMarketNorth!, 'coal_north', -92, { side: 'north' },
            );
            this.oilsNorth = this.buildMainRowPieces(
                gameState.oilPricesNorth!, gameState.oilMarketNorth!, 'oil_north', -70, { side: 'north' },
            );
            this.garbagesNorth = this.buildMainRowPieces(
                gameState.garbagePricesNorth!, gameState.garbageMarketNorth!, 'garbage_north', -46, { side: 'north' },
            );

            return;
        }

        // Europe and North America: 9 price spaces ($1..$9), per-price slot count
        // varies by resource, and uranium tops out at $9 (no $10/$12/$14/$16 corner).
        // Rows are spaced apart (uranium between oil and garbage) so each cube
        // is comfortably clickable: oil 70 → uranium 92 → garbage 106.
        if (gameState.map?.name === 'Europe' || gameState.map?.name === 'North America') {
            this.isNinePriceMarket = true;
            this.coals = this.buildMainRowPieces(
                gameState.coalPrices!, gameState.coalMarket, 'coal', 48, { maxPrice: 9 },
            );
            this.oils = this.buildMainRowPieces(
                gameState.oilPrices!, gameState.oilMarket, 'oil', 70, { maxPrice: 9 },
            );
            this.uraniums = this.buildMainRowPieces(
                gameState.uraniumPrices!, gameState.uraniumMarket, 'uranium', 92, { maxPrice: 9 },
            );
            this.garbages = this.buildMainRowPieces(
                gameState.garbagePrices!, gameState.garbageMarket, 'garbage', 106, { maxPrice: 9 },
            );
            return;
        }
        this.isNinePriceMarket = false;

        // Non-Korea: original logic below (unchanged).
        this.coalsNorth = [];
        this.oilsNorth = [];
        this.garbagesNorth = [];

        {
            this.coals = [];
            if (gameState.map?.name == 'India') {
                Array(24)
                    .fill(0)
                    .forEach((_, i) => {
                        // Convert i to which of the 32 slots it belongs in, some of which are empty.
                        let index = i;
                        if (i >= 0) {
                            index += 2; // 2 empty slots for $8
                        }
                        if (i >= 2) {
                            index += 2; // 2 empty slots for $7
                        }
                        if (i >= 4) {
                            index++; // 1 empty slot for $6
                        }
                        if (i >= 7) {
                            index++; // 1 empty slot for $5
                        }
                        if (i >= 10) {
                            index++; // 1 empty slot for $4
                        }
                        if (i >= 13) {
                            index++; // 1 empty slot for $3
                        }

                        this.coals.push({
                            id: 'coal_' + i,
                            x: 672 - 17 * index - 17 * Math.floor(index / 4),
                            y: 48,
                            transparent: i >= gameState!.coalMarket
                        });
                    });
            } else {
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
            }

            if (gameState.options.variant == 'recharged' && gameState.map?.name == 'USA') {
                range(gameState.coalSupply).forEach((i) => {
                    this.coals.push({
                        id: 'coal_supply_' + i,
                        x: 800 + (i % 8) * 20 + (i >= 8 && i < 16 ? 10 : 0),
                        y: 50 + Math.floor(i / 8) * 20,
                        transparent: false,
                    });
                });
            }

            // South Africa: storage pool cubes. Always $8, clickable when buyable.
            if (gameState.coalStorage !== undefined) {
                range(gameState.coalStorage).forEach((i) => {
                    this.coals.push({
                        id: 'coal_storage_' + i,
                        x: 800 + (i % 8) * 20 + (i >= 8 && i < 16 ? 10 : 0),
                        y: 50 + Math.floor(i / 8) * 20,
                        transparent: false,
                        fromStorage: true,
                    });
                });
            }

            this.oils = [];
            if (gameState.map?.name == 'Middle East') {
                let maxRegularOil = gameState.oilPrices!.filter(p => p > 1).length;
                let maxSurplusOil = gameState.oilPrices!.filter(p => p == 1).length;
                let availableRegularOil = Math.min(maxRegularOil, gameState.oilMarket);

                Array(maxRegularOil)
                    .fill(0)
                    .forEach((_, i) => {
                        let adjustedIndex = i + (maxSurplusOil - 3);
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
            if (gameState.map?.name == 'India') {
                Array(24)
                    .fill(0)
                    .forEach((_, i) => {
                        let index = i + 8; // Leave $7 and $8 empty.
                        this.garbages.push({
                            id: 'garbage_' + i,
                            x: 672 - 17 * index - 17 * Math.floor(index / 4),
                            y: 94,
                            transparent: i >= gameState!.garbageMarket,
                        });
                    });
            } else {
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
            }

            this.uraniums = [];
            if (gameState.map?.name == 'India') {
                Array(8)
                    .fill(0)
                    .forEach((_, i) => {
                        this.uraniums.push({
                            id: 'uranium_' + i,
                            x: 670 - 85 * i,
                            y: 72,
                            transparent: i >= gameState!.uraniumMarket
                        });
                    });
            } else {
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
    }

    canBuyResource(resource: string, side?: 'north' | 'south', fromStorage?: boolean) {
        return !!this.buyableResources!.find(
            (r) => r.resource == resource && r.side == side && !!r.fromStorage == !!fromStorage,
        );
    }

    get hasBuyableNorth() {
        return !!this.buyableResources?.some(r => r.side === 'north');
    }

    get hasBuyableSouth() {
        return !!this.buyableResources?.some(r => r.side === 'south');
    }

    buyResource(resource: string, side?: 'north' | 'south', fromStorage?: boolean) {
        this.$emit('buyResource', { resource, side, fromStorage });
    }
}
</script>
