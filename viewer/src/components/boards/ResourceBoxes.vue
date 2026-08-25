<template>
    <g>
        <template v-for="(block, b) in blocks">
            <g :key="'block' + b" :transform="`translate(0, ${block.y})`">
                <text v-if="block.title" x="4" y="16" font-weight="700" fill="black" style="font-size: 26px">
                    {{ block.title }}
                </text>

                <!-- Restock, as the printed refill card reads it: one number per row,
                     in the same order the rows are drawn. -->
                <text
                    v-if="block.restock"
                    :x="BOX_W - 4"
                    y="16"
                    text-anchor="end"
                    font-weight="600"
                    fill="#3a2c08"
                    style="font-size: 24px"
                >
                    Restock {{ block.restock }}
                </text>

                <text x="4" y="42" fill="#3a2c08" style="font-size: 24px; letter-spacing: 1px">CURRENT PRICE</text>
                <text
                    :x="CUBE_BAND_CENTRE"
                    y="42"
                    text-anchor="middle"
                    fill="#3a2c08"
                    style="font-size: 24px; letter-spacing: 1px"
                >
                    AT THIS PRICE
                </text>
                <text
                    :x="BOX_W - 4"
                    y="42"
                    text-anchor="end"
                    fill="#3a2c08"
                    style="font-size: 24px; letter-spacing: 1px"
                >
                    CUBES LEFT
                </text>

                <g
                    v-for="(row, r) in block.rows"
                    :key="'row' + r"
                    :transform="`translate(0, ${HEAD_H + r * (BOX_H + BOX_GAP)})`"
                    :class="[{ canClick: row.buyable }]"
                    @click="row.buyable && $emit('buyResource', row.move)"
                >
                    <rect
                        :width="BOX_W"
                        :height="BOX_H"
                        rx="6"
                        :fill="row.cubes > 0 ? 'darkgoldenrod' : '#9c8236'"
                        :stroke="row.buyable ? '#1e63d0' : '#6b5312'"
                        :stroke-width="row.buyable ? 5 : 2"
                        :opacity="row.cubes > 0 ? 1 : 0.55"
                    />
                    <!-- Whole box is the tap target, cubes and all. -->
                    <rect
                        v-if="row.buyable"
                        :width="BOX_W"
                        :height="BOX_H"
                        rx="6"
                        fill="transparent"
                        pointer-events="all"
                    />

                    <text x="18" y="26" font-weight="700" fill="black" style="font-size: 22px; letter-spacing: 1px">
                        {{ row.label }}
                    </text>

                    <template v-if="row.price != null">
                        <text x="18" y="80" font-weight="700" fill="black" style="font-size: 26px">$</text>
                        <text x="40" y="84" font-weight="700" fill="black" style="font-size: 46px">
                            {{ row.price }}
                        </text>
                        <text v-if="row.next != null" x="132" y="80" fill="#3a2c08" style="font-size: 22px">
                            then ${{ row.next }}
                        </text>
                    </template>
                    <text v-else x="18" y="78" font-weight="700" fill="black" style="font-size: 28px">out</text>

                    <!-- One dot per cube still buyable at the current price. A pool
                         with no price track behind it has no such number: every cube
                         in it costs the same, so say that instead of drawing dots. -->
                    <circle
                        v-for="n in row.atPrice"
                        :key="'cube' + n"
                        :cx="cubeX(row.atPrice, n)"
                        :cy="58"
                        r="17"
                        :fill="row.color"
                        stroke="black"
                        stroke-width="2"
                    />
                    <text v-if="row.flat && row.cubes > 0" x="300" y="66" fill="#3a2c08" style="font-size: 22px">
                        every cube at this price
                    </text>

                    <text
                        :x="BOX_W - 18"
                        y="68"
                        text-anchor="end"
                        font-weight="700"
                        fill="black"
                        style="font-size: 40px"
                    >
                        {{ row.cubes }}
                    </text>
                    <text :x="BOX_W - 18" y="90" text-anchor="end" fill="#3a2c08" style="font-size: 20px">LEFT</text>

                    <!-- India caps which prices are on sale per step; a row above the
                         cap is on the board but cannot be bought by anyone yet. -->
                    <text v-if="row.capped" x="130" y="96" fill="#7a1d12" font-weight="600" style="font-size: 20px">
                        step {{ step }} sells to ${{ maxPrice }}
                    </text>

                    <!-- A purchase made this turn can be handed back (#127). The box
                         market has no empty spaces to click — the printed track's
                         ghosts are exactly what it replaces — so the take-back lives
                         on a chip, and stops the click reaching the buy target under
                         it. Sits in the free band above the cubes, and appears whether
                         or not the row is still buyable: being unable to afford the
                         next cube is precisely when you want the last one back. -->
                    <g v-if="canUnbuy(row)" class="canClick" @click.stop="$emit('unbuyResource', row.move)">
                        <rect
                            :x="chipBox(row).hx"
                            :y="chipBox(row).hy"
                            :width="chipBox(row).hw"
                            :height="chipBox(row).hh"
                            fill="transparent"
                            pointer-events="all"
                        />
                        <rect
                            :x="chipBox(row).x"
                            :y="chipBox(row).y"
                            :width="chipBox(row).w"
                            :height="chipBox(row).h"
                            rx="10"
                            fill="#f0e6c8"
                            stroke="#6b5312"
                            stroke-width="2"
                        />
                        <text
                            :x="chipBox(row).x + chipBox(row).w / 2"
                            :y="chipBox(row).y + chipBox(row).h / 2 + 8"
                            text-anchor="middle"
                            font-weight="700"
                            fill="#3a2c08"
                            :style="`font-size: ${chipBox(row).fontSize}px`"
                        >
                            − take back
                        </text>
                    </g>

                    <title>{{ row.title }}</title>
                </g>
            </g>
        </template>
    </g>
</template>

<script lang="ts">
import { GameState } from 'powergrid-engine';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { BuyMove, ResourceBlock, ResourceRow, resourceBlocks } from '../../util/resource-rows';
import { buySourceKey } from '../../util/turn-buffer';

const BOX_W = 700;
const BOX_H = 104;
const BOX_GAP = 8;
/** Block title + column captions above the first box. */
const HEAD_H = 62;
const BLOCK_GAP = 30;
const CUBE_PITCH = 44;
/** Middle of the band between the price block and the cubes-left count. */
const CUBE_BAND_CENTRE = 420;

/**
 * The portrait resource market.
 *
 * The printed price track is a beautiful object and an unreadable one on a phone:
 * eight to ten columns of three-cube slots, drawn at whatever width the map author
 * chose and then squeezed into a strip. This draws the same market as one box per
 * buyable source, carrying only what a purchase actually needs — what the next cube
 * costs, how many are left at that price, how many are left at all.
 *
 * Every number comes out of the engine state rather than the printed geometry, so the
 * map-specific markets come along for free: Europe's nine price columns, Korea's two
 * sides, Australia's Step-3 CO2 shift (the engine rewrites the price array and the box
 * is only ever a view of it), India's per-step price cap, South Africa's $8 storage
 * pool, USA recharged's $8-from-supply once the track is bare.
 *
 * Which rows a player may actually tap is NOT decided here: `buyableResources` is the
 * engine's own availableMoves, so money, storage capacity, the hybrid tank and Korea's
 * side lock are all accounted for already. The row model itself lives in
 * `util/resource-rows`, where it can be tested against the engine's own arithmetic.
 */
@Component
export default class ResourceBoxes extends Vue {
    @Prop() gameState!: GameState;
    @Prop() buyableResources?: BuyMove[];
    @Prop() resourceResupply?: (number | string)[];
    @Prop() resourceResupplyNorth?: (number | string)[];
    @Prop() isUsaRecharged?: boolean;
    /** The seat looking at the board — only needed for Central Europe's Wien discount. */
    @Prop() player?: number;
    /** Purchases still sitting in this turn's buffer, per source (#127). */
    @Prop() bufferedBuys?: Record<string, number>;

    BOX_W = BOX_W;
    BOX_H = BOX_H;
    BOX_GAP = BOX_GAP;
    HEAD_H = HEAD_H;
    CUBE_BAND_CENTRE = CUBE_BAND_CENTRE;

    /**
     * Where a row's take-back button sits: in the gap between the price block and the
     * cubes, and big enough for a thumb (~28 css px tall on a phone).
     *
     * The two pool rows carry a long label right across that gap — but they are
     * flat-priced, so nothing sits below them, and the button drops under the label at
     * the same size rather than shrinking.
     */
    chipBox(row: ResourceRow) {
        const labelFillsTheTop = row.label.length > 8;

        return labelFillsTheTop
            ? { x: 130, y: 36, w: 140, h: 52, hx: 120, hy: 32, hw: 164, hh: 60, fontSize: 22 }
            : { x: 130, y: 6, w: 140, h: 52, hx: 120, hy: 2, hw: 164, hh: 60, fontSize: 22 };
    }

    /** Does this turn's buffer hold a purchase from this row's source? */
    canUnbuy(row: ResourceRow): boolean {
        return !!this.bufferedBuys && !!this.bufferedBuys[buySourceKey(row.move)];
    }

    /** Centre the cube cluster in that band, however many cubes there are. */
    cubeX(count: number, n: number): number {
        return CUBE_BAND_CENTRE - ((count - 1) * CUBE_PITCH) / 2 + (n - 1) * CUBE_PITCH;
    }

    get step(): number {
        return this.gameState.step;
    }

    get maxPrice(): number {
        const table = (this.gameState.map as { maxPriceAvailable?: number[] }).maxPriceAvailable;
        return table ? table[this.gameState.step - 1] : 16;
    }

    get blocks(): (ResourceBlock & { y: number })[] {
        let y = 0;
        return resourceBlocks(this.gameState, {
            player: this.player,
            buyable: this.buyableResources,
            resupply: this.resourceResupply,
            resupplyNorth: this.resourceResupplyNorth,
            isUsaRecharged: this.isUsaRecharged,
        }).map((block) => {
            const placed = { ...block, y };
            y += HEAD_H + block.rows.length * (BOX_H + BOX_GAP) - BOX_GAP + BLOCK_GAP;
            return placed;
        });
    }
}
</script>

<style lang="scss" scoped>
.canClick {
    cursor: pointer;
}
</style>
