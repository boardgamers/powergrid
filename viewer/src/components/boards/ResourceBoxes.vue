<template>
    <g class="resource-cards">
        <g v-for="(block, b) in blocks" :key="'block' + b" :transform="`translate(0, ${block.y})`">
            <text v-if="block.title" x="4" y="28" font-weight="700" fill="black" font-size="28">{{ block.title }}</text>
            <g
                v-for="row in block.rows"
                :key="sourceKey(row)"
                :transform="`translate(0, ${row.y})`"
                :data-resource-card="sourceKey(row)"
            >
                <rect width="700" :height="rowHeight(row)" rx="9" fill="#f4e5a8" stroke="#806b28" stroke-width="2" />

                <!-- Buying and inspecting stock are separate, generous tap targets. -->
                <g
                    :class="{ canClick: row.buyable }"
                    role="button"
                    :tabindex="row.buyable ? 0 : -1"
                    :aria-disabled="!row.buyable"
                    :aria-label="row.title"
                    data-buy-resource
                    @click.stop="row.buyable && $emit('buyResource', row.move)"
                    @keydown.enter.prevent="row.buyable && $emit('buyResource', row.move)"
                    @keydown.space.prevent="row.buyable && $emit('buyResource', row.move)"
                >
                    <rect width="374" height="110" fill="transparent" pointer-events="all" />
                    <path
                        :d="isExpanded(row) ? 'M9 1H374V110H1V9Q1 1 9 1Z' : 'M9 1H374V109H9Q1 109 1 101V9Q1 1 9 1Z'"
                        fill="#d9b54a"
                        :stroke="row.buyable ? '#1e63d0' : 'none'"
                        stroke-width="4"
                    />
                    <text
                        v-if="row.flat"
                        x="20"
                        y="28"
                        dominant-baseline="middle"
                        font-weight="700"
                        fill="#34402a"
                        :font-size="row.label.length > 14 ? 22 : 27"
                        >{{ row.label }}</text
                    >
                    <g :transform="`translate(20, ${row.flat ? 48 : 31})`"><ResourceCost :amount="row.price" /></g>
                    <g v-if="!row.flat" transform="translate(115, 37)" data-current-price-tokens>
                        <g
                            v-for="n in Math.max(1, Math.min(3, row.atPrice))"
                            :key="n"
                            :opacity="row.atPrice === 0 ? 0.3 : 1"
                            :transform="`translate(${(n - 1) * 33}, 0)`"
                        >
                            <ResourceToken :resource="row.move.resource" :size="35" />
                        </g>
                        <text
                            v-if="row.atPrice > 3"
                            x="102"
                            y="20"
                            dominant-baseline="middle"
                            font-size="24"
                            fill="#3a2c08"
                            >+{{ row.atPrice - 3 }}</text
                        >
                    </g>
                    <g v-if="row.next != null">
                        <path
                            d="M253 55 h22 m-8 -8 8 8 -8 8"
                            fill="none"
                            stroke="#806b28"
                            stroke-width="3"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        />
                        <g transform="translate(290, 35) scale(0.85)"
                            ><ResourceCost :amount="row.next" :muted="true"
                        /></g>
                        <title>then ${{ row.next }}</title>
                    </g>
                    <title>{{ row.title }}</title>
                </g>

                <g
                    :class="{ canClick: canUnbuy(row) }"
                    role="button"
                    :tabindex="canUnbuy(row) ? 0 : -1"
                    :aria-disabled="!canUnbuy(row)"
                    :opacity="canUnbuy(row) ? 1 : 0.35"
                    data-unbuy-resource
                    :data-staged-count="stagedCount(row)"
                    :aria-label="`${row.label}: ${stagedCount(row)} · − take back`"
                    @click.stop="canUnbuy(row) && $emit('unbuyResource', row.move)"
                    @keydown.enter.prevent="canUnbuy(row) && $emit('unbuyResource', row.move)"
                    @keydown.space.prevent="canUnbuy(row) && $emit('unbuyResource', row.move)"
                >
                    <rect x="374" y="1" width="116" height="108" fill="#f0e6c8" pointer-events="all" />
                    <g v-if="canUnbuy(row)" data-staged-tokens>
                        <g transform="translate(394, 16)"><ResourceToken :resource="row.move.resource" :size="29" /></g>
                        <text
                            x="455"
                            y="32"
                            text-anchor="middle"
                            dominant-baseline="middle"
                            font-size="30"
                            font-weight="700"
                            fill="#3a2c08"
                            >{{ stagedCount(row) }}</text
                        >
                    </g>
                    <text
                        x="432"
                        :y="canUnbuy(row) ? 79 : 56"
                        text-anchor="middle"
                        dominant-baseline="middle"
                        :font-size="canUnbuy(row) ? 38 : 48"
                        fill="#3a2c08"
                        >↶</text
                    >
                    <title>{{ row.label }}: {{ stagedCount(row) }} · − take back</title>
                </g>

                <line x1="490" x2="490" y1="1" y2="109" stroke="#b9a267" stroke-width="1.5" pointer-events="none" />

                <g
                    class="canClick"
                    role="button"
                    tabindex="0"
                    :aria-expanded="isExpanded(row) ? 'true' : 'false'"
                    :aria-label="row.label + ': Price track'"
                    data-resource-details
                    @click="toggle(row)"
                    @keydown.enter.prevent="toggle(row)"
                    @keydown.space.prevent="toggle(row)"
                >
                    <rect x="490" y="0" width="210" height="110" fill="transparent" pointer-events="all" />
                    <template v-if="!row.flat">
                        <g transform="translate(512, 15)">
                            <ResourceToken :resource="row.move.resource" :size="25" />
                            <g transform="translate(9, 8)"
                                ><ResourceToken :resource="row.move.resource" :size="25"
                            /></g>
                        </g>
                        <text
                            x="591"
                            y="31"
                            text-anchor="middle"
                            dominant-baseline="middle"
                            font-weight="700"
                            font-size="32"
                            fill="#34402a"
                            >{{ row.cubes }}</text
                        >
                        <g transform="translate(515, 63) scale(1.1)"><ResupplyIcon /></g>
                        <text
                            x="591"
                            y="79"
                            text-anchor="middle"
                            dominant-baseline="middle"
                            font-weight="600"
                            font-size="27"
                            fill="#34402a"
                            >+{{ restockFor(row, currentStep) }}</text
                        >
                    </template>
                    <template v-else>
                        <g transform="translate(512, 39)">
                            <ResourceToken :resource="row.move.resource" :size="25" />
                            <g transform="translate(9, 8)"
                                ><ResourceToken :resource="row.move.resource" :size="25"
                            /></g>
                        </g>
                        <text
                            x="591"
                            y="55"
                            text-anchor="middle"
                            dominant-baseline="middle"
                            font-weight="700"
                            font-size="36"
                            fill="#34402a"
                            >{{ row.cubes }}</text
                        >
                    </template>
                    <path
                        :d="isExpanded(row) ? 'M647 62 l13 -13 13 13' : 'M647 49 l13 13 13 -13'"
                        fill="none"
                        stroke="#806b28"
                        stroke-width="3"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                    />
                    <title>Price track</title>
                </g>

                <g v-if="isExpanded(row)" data-price-breakdown transform="translate(14, 115)">
                    <g
                        v-for="(tier, i) in row.tiers"
                        :key="tier.price"
                        :transform="`translate(${(i % 6) * 113}, ${Math.floor(i / 6) * 112})`"
                        :data-price="tier.price"
                        :class="{ canClick: canBuyTier(row, tier.price) }"
                        :role="canBuyTier(row, tier.price) ? 'button' : undefined"
                        :tabindex="canBuyTier(row, tier.price) ? 0 : undefined"
                        :aria-label="canBuyTier(row, tier.price) ? row.title : undefined"
                        :data-buy-tier="canBuyTier(row, tier.price) ? 'true' : undefined"
                        @click.stop="canBuyTier(row, tier.price) && $emit('buyResource', row.move)"
                        @keydown.enter.prevent="canBuyTier(row, tier.price) && $emit('buyResource', row.move)"
                        @keydown.space.prevent="canBuyTier(row, tier.price) && $emit('buyResource', row.move)"
                        :data-cubes="tier.cubes"
                        :opacity="tier.cubes === 0 ? 0.38 : tier.capped ? 0.6 : 1"
                    >
                        <rect
                            v-if="canBuyTier(row, tier.price)"
                            x="-3"
                            y="-3"
                            width="112"
                            height="110"
                            fill="transparent"
                            pointer-events="all"
                        />
                        <rect
                            width="106"
                            height="104"
                            rx="5"
                            :fill="tier.price === row.price ? '#e5cc83' : '#faefc9'"
                            :stroke="
                                canBuyTier(row, tier.price)
                                    ? '#1e63d0'
                                    : tier.price === row.price
                                    ? '#665320'
                                    : '#cbb774'
                            "
                            :stroke-width="tier.price === row.price ? 2 : 1"
                            :stroke-dasharray="tier.capped ? '5 3' : undefined"
                        />
                        <g transform="translate(26.5, 12) scale(0.68)"
                            ><ResourceCost :amount="tier.price" :muted="tier.price !== row.price"
                        /></g>
                        <g
                            v-for="n in tier.cubes > 3 ? 2 : tier.cubes"
                            :key="'token' + n"
                            :transform="`translate(${
                                (tier.cubes > 3 ? 3 : (106 - tier.cubes * 26) / 2) + (n - 1) * 26
                            }, 59)`"
                        >
                            <ResourceToken :resource="row.move.resource" :size="26" />
                        </g>
                        <text v-if="tier.cubes === 0" x="53" y="81" text-anchor="middle" font-size="25" fill="#3a2c08"
                            >—</text
                        >
                        <text
                            v-if="tier.cubes > 3"
                            x="99"
                            y="82"
                            text-anchor="end"
                            font-size="21"
                            font-weight="700"
                            fill="#26351a"
                            >+{{ tier.cubes - 2 }}</text
                        >
                    </g>
                    <text v-if="row.capped" x="2" :y="breakdownHeight(row) - 10" font-size="23" fill="#7a1d12"
                        >step {{ step }} sells to ${{ maxPrice }}</text
                    >
                </g>

                <!-- All three rates fit in one line; no tiny step buttons on phones. -->
                <g
                    v-if="!row.flat && isExpanded(row)"
                    :transform="`translate(0, ${110 + breakdownHeight(row)})`"
                    data-refill-rates
                >
                    <g transform="translate(50, 2) scale(1.7)"><ResupplyIcon /></g>
                    <g
                        v-for="s in 3"
                        :key="s"
                        :transform="`translate(${145 + (s - 1) * 180}, 0)`"
                        :opacity="s < currentStep ? 0.45 : 1"
                    >
                        <rect width="164" height="44" rx="5" :fill="s === currentStep ? '#e5cc83' : 'none'" />
                        <text x="13" y="23" dominant-baseline="middle" font-size="24" fill="#3a2c08">S{{ s }}</text>
                        <text
                            x="151"
                            y="23"
                            dominant-baseline="middle"
                            text-anchor="end"
                            font-size="26"
                            font-weight="600"
                            fill="#26351a"
                            >+{{ restockFor(row, s) }}</text
                        >
                        <line
                            v-if="s === currentStep"
                            x1="13"
                            x2="42"
                            y1="38"
                            y2="38"
                            stroke="#b68b00"
                            stroke-width="2"
                        />
                        <title>Resource Resupply: {{ restockFor(row, s) }}</title>
                    </g>
                </g>
            </g>
        </g>
    </g>
</template>

<script lang="ts">
import { GameState } from 'powergrid-engine';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { BuyMove, ResourceRow, resourceBlocks } from '../../util/resource-rows';
import { buySourceKey } from '../../util/turn-buffer';
import ResourceToken from './ResourceToken.vue';
import ResourceCost from './ResourceCost.vue';
import ResupplyIcon from './ResupplyIcon.vue';

@Component({ components: { ResourceToken, ResourceCost, ResupplyIcon } })
export default class ResourceBoxes extends Vue {
    @Prop({ default: 1 }) currentStep!: number;
    @Prop() gameState!: GameState;
    @Prop() buyableResources?: BuyMove[];
    @Prop() isUsaRecharged?: boolean;
    @Prop() player?: number;
    @Prop() bufferedBuys?: Record<string, number>;
    expanded: Record<string, boolean> = {};

    sourceKey(row: ResourceRow): string { return buySourceKey(row.move); }
    canBuyTier(row: ResourceRow, price: number): boolean { return row.buyable && row.price === price; }
    isExpanded(row: ResourceRow): boolean { return !!this.expanded[this.sourceKey(row)]; }
    toggle(row: ResourceRow) {
        this.$set(this.expanded, this.sourceKey(row), !this.isExpanded(row));
        this.$nextTick(() => this.$emit('resize'));
    }
    stagedCount(row: ResourceRow): number { return this.bufferedBuys?.[this.sourceKey(row)] || 0; }
    canUnbuy(row: ResourceRow): boolean { return this.stagedCount(row) > 0; }
    breakdownHeight(row: ResourceRow): number { return Math.ceil(row.tiers.length / 6) * 112 + (row.capped ? 32 : 0); }
    rowHeight(row: ResourceRow): number { return 110 + (this.isExpanded(row) ? this.breakdownHeight(row) + (row.flat ? 0 : 50) : 0); }
    restockFor(row: ResourceRow, step: number): string {
        const table = row.move.side === 'north' ? this.gameState.resourceResupplyNorth : this.gameState.resourceResupply;
        const index = ['coal', 'oil', 'garbage', 'uranium'].indexOf(row.move.resource);
        return table ? table[step - 1].slice(1, -1).split(',')[index].trim() : '0';
    }
    get step(): number { return this.gameState.step; }
    get maxPrice(): number {
        const table = (this.gameState.map as { maxPriceAvailable?: number[] }).maxPriceAvailable;
        return table ? table[this.gameState.step - 1] : 16;
    }
    get blocks() {
        let y = 0;
        return resourceBlocks(this.gameState, { player: this.player, buyable: this.buyableResources, isUsaRecharged: this.isUsaRecharged }).map(block => {
            const blockY = y;
            let rowY = block.title ? 44 : 0;
            const rows = block.rows.map(row => {
                const placed = { ...row, y: rowY };
                rowY += this.rowHeight(row) + 14;
                return placed;
            });
            y += rowY + 16;
            return { ...block, rows, y: blockY };
        });
    }
}
</script>

<style lang="scss" scoped>
.canClick {
    cursor: pointer;
}
[role='button'] {
    touch-action: manipulation;
    user-select: none;
    -webkit-user-select: none;
}
[role='button']:focus-visible {
    outline: 3px solid #1e63d0;
    outline-offset: 2px;
}
</style>
