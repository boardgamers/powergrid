<template>
    <g class="city-count-track">
        <g v-for="row in compact ? 2 : 1" :key="'row' + row" :transform="`translate(0, ${(row - 1) * 70})`">
            <rect :width="compact ? 367 : 730" height="68" x="10" y="10" rx="3" fill="goldenrod" />
            <rect :width="compact ? 359 : 722" height="20" x="14" y="56" rx="2" fill="#365343" />
        </g>
        <g
            v-for="(income, count) in paymentTable"
            :key="count"
            :transform="`translate(${cellX(count)}, ${cellY(count)})`"
        >
            <title>
                {{
                    `Cities supplied: ${count}. Income: $${income} before map penalties. Houses show connected cities.`
                }}
            </title>
            <rect
                width="28"
                height="38"
                x="13"
                y="14"
                rx="2"
                fill="darkgoldenrod"
                :stroke="count == citiesToStep2 || count == citiesToEndGame ? '#916a08' : 'darkgoldenrod'"
                stroke-width="2px"
            />
            <text
                text-anchor="middle"
                style="font-size: 24px; font-family: monospace"
                letter-spacing="-2"
                x="26"
                y="27"
                fill="gold"
            >
                {{ count }}
            </text>
            <line v-if="count % (compact ? 11 : 22) > 0" x1="10.5" x2="10.5" y1="61" y2="71" stroke="#607765" />
            <text
                class="city-income"
                x="27"
                y="66"
                text-anchor="middle"
                style="font-size: 15px; dominant-baseline: central"
                fill="#fff3cf"
            >
                {{ income }}
            </text>
        </g>
        <!-- Keep row placement synchronous so the portrait layout measures the new track bounds. -->
        <g
            v-for="house in houses"
            :key="house.id"
            :transform="`translate(${cellX(house.cityCount)}, ${cellY(house.cityCount)})`"
        >
            <House
                :pieceId="house.id"
                :targetState="{ x: house.x, y: house.y }"
                :owner="house.owner"
                :ownerName="house.ownerName"
                :color="house.color"
                :scale="0.03"
            />
        </g>
        <g class="city-income-legend" :transform="`translate(0, ${compact ? 157 : 87})`">
            <circle cx="21" cy="0" r="7" fill="#365343" />
            <text x="21" text-anchor="middle" font-size="11" fill="#fff3cf">$</text>
            <text x="33" y="0" style="font-size: 13px; dominant-baseline: central" fill="#29432e">
                Total income for powered cities
            </text>
        </g>
    </g>
</template>

<script lang="ts">
import type { GameState } from 'powergrid-engine';
import { Vue, Component, Prop } from 'vue-property-decorator';
import { House } from '../pieces';
import { Piece } from '../../types/ui-data';

// The House piece at the 0.03 scale this track draws it, rounded to whole units: the
// path spans 3-396 x 4-456, so 12 x 14 on the board. Used as the grid pitch below.
const HOUSE_WIDTH = 12;
const HOUSE_HEIGHT = 14;
// The cell rect the template draws at x 13 y 14, 28 x 38 — houses are placed against
// its bottom edge, clear of the income strip that starts 4 units below it.
const CELL_CENTRE_X = 27;
const CELL_BOTTOM = 52;

@Component({
    components: {
        House
    },
})
export default class CityCount extends Vue {
    @Prop() citiesToStep2?: number;
    @Prop() citiesToEndGame?: number;
    @Prop() playerColors?: string[];
    @Prop({ required: true }) paymentTable!: number[];
    @Prop({ default: false }) compact!: boolean;

    houses: (Piece & { cityCount: number })[] = [];

    cellX(count: number) {
        return 33 * (this.compact ? count % 11 : count);
    }

    cellY(count: number) {
        return this.compact ? Math.floor(count / 11) * 70 : 0;
    }

    createPieces(gameState: GameState) {
        this.houses = [];
        const adjustCityCount: number[][] = [];
        for (let i = 0; i < 22; i++) adjustCityCount[i] = [];

        gameState.players.forEach((player, pi) => adjustCityCount[player.cities.length].push(pi));
        gameState.players.forEach((player, pi) => {
            // Players sharing a count get a grid, bottom-aligned in the cell so it grows
            // upward from the income strip and leaves the digit above readable. At the
            // old 6px/3px offsets even TWO players on the same number — the ordinary
            // case all game — overlapped by half and read as one smudge.
            //
            // Five or six share go three wide rather than three tall: a third row starts
            // at the top of the cell and hides the number completely, which is every
            // game's opening position. Three columns only have to overlap by a few
            // pixels, and the cells are spaced wider than they are drawn.
            const sharing = adjustCityCount[player.cities.length];
            const seat = sharing.indexOf(pi);
            const cols = sharing.length > 4 ? 3 : 2;
            const pitch = cols === 3 ? 9 : HOUSE_WIDTH;
            const rows = Math.ceil(sharing.length / cols);

            this.houses.push({
                id: pi + '_cityCount',
                cityCount: player.cities.length,
                // CELL_CENTRE_X/BOTTOM are the darkgoldenrod cell drawn in the template.
                x:
                    sharing.length == 1
                        ? CELL_CENTRE_X - HOUSE_WIDTH / 2
                        : CELL_CENTRE_X - ((cols - 1) * pitch + HOUSE_WIDTH) / 2 + (seat % cols) * pitch,
                y: CELL_BOTTOM - rows * HOUSE_HEIGHT + Math.floor(seat / cols) * HOUSE_HEIGHT,
                color: this.playerColors![pi],
                owner: pi,
                ownerName: player.name,
            });
        });
    }
}
</script>
