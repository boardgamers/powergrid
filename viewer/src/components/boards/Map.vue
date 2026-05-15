<template>
    <g @click="onPickCoord">
        <!-- Dev-only backdrop for coord-picking. See GameMap.devBackdrop. -->
        <image
            v-if="devBackdrop"
            :href="devBackdrop.src"
            x="0"
            y="0"
            :width="devBackdrop.width"
            :height="devBackdrop.height"
            :opacity="devBackdrop.opacity != null ? devBackdrop.opacity : 0.5"
        />

        <!-- <template v-for="polygon in polygons">
            <polygon
                :key="'pol_ ' + polygon.region"
                :points="polygon.points.map((p) => `${p[0]},${p[1]}`).join(' ')"
                :fill="polygon.region"
                opacity="0.8"
                stroke="black"
            ></polygon>
        </template> -->

        <template v-for="city in cities">
            <circle :key="city.name + '_region'" r="25" :cx="city.x" :cy="city.y" :fill="city.region" stroke="black">
                <title>{{ city.name }}</title>
            </circle>
            <circle :key="city.name + '_circle'" r="20" :cx="city.x" :cy="city.y" fill="gray" stroke="black">
                <title>{{ city.name }}</title>
            </circle>
            <!-- South Africa cross-border spaces: render a small red pennant
                 above the city. Marks a single-occupancy space ($30 total cost). -->
            <g v-if="city.singleOccupancy" :key="city.name + '_flag'">
                <line
                    :x1="city.x + 12"
                    :y1="city.y - 12"
                    :x2="city.x + 12"
                    :y2="city.y - 32"
                    stroke="black"
                    stroke-width="1.5"
                />
                <polygon
                    :points="`${city.x + 12},${city.y - 32} ${city.x + 26},${city.y - 28} ${city.x + 12},${
                        city.y - 24
                    }`"
                    fill="red"
                    stroke="black"
                    stroke-width="1"
                />
                <title>{{ city.name }} — cross-border space (1 house max, 30 Elektro total cost)</title>
            </g>
        </template>

        <template v-for="connection in connections">
            <line
                :key="connection.nodes[0] + '_' + connection.nodes[1] + '_line1'"
                :x1="getX1(connection)"
                :y1="getY1(connection)"
                :x2="getX2(connection)"
                :y2="getY2(connection)"
                stroke-width="10"
                stroke="black"
            />
            <line
                :key="connection.nodes[0] + '_' + connection.nodes[1] + '_line2'"
                :x1="getX1(connection)"
                :y1="getY1(connection)"
                :x2="getX2(connection)"
                :y2="getY2(connection)"
                stroke-width="9"
                stroke="gray"
            />
        </template>

        <template v-for="city in cities">
            <circle
                :key="city.name + '_circle2'"
                :class="[{ canClick: canBuild(city) }]"
                r="20"
                :cx="city.x"
                :cy="city.y"
                fill="gray"
                @click="canBuild(city) && build(city)"
            >
                <title>{{ city.name }}</title>
            </circle>
        </template>

        <template v-for="connection in connections">
            <circle
                v-if="connection.cost > 0"
                :key="connection.nodes[0] + '_' + connection.nodes[1] + '_border'"
                stroke="black"
                :r="10 + (connection.cost * 10) / 28"
                :cx="(getX1(connection) + getX2(connection)) / 2"
                :cy="(getY1(connection) + getY2(connection)) / 2"
                :fill="connection.cost > 15 ? 'gold' : connection.cost > 10 ? 'lightgray' : 'tan'"
            />
            <circle
                v-if="connection.cost > 0"
                :key="connection.nodes[0] + '_' + connection.nodes[1] + '_circle'"
                :r="6 + (connection.cost * 10) / 28"
                :cx="(getX1(connection) + getX2(connection)) / 2"
                :cy="(getY1(connection) + getY2(connection)) / 2"
                fill="gray"
                stroke="black"
            />
            <text
                v-if="connection.cost > 0"
                :key="connection.nodes[0] + '_' + connection.nodes[1] + '_text'"
                text-anchor="middle"
                :style="`font-size: ${12 + (connection.cost * 6) / 28}px`"
                fill="black"
                :x="(getX1(connection) + getX2(connection)) / 2"
                :y="(getY1(connection) + getY2(connection)) / 2"
            >
                {{ connection.cost }}
            </text>
        </template>
        <template v-for="house in houses">
            <House
                :key="house.id"
                :pieceId="house.id"
                :targetState="{ x: house.x, y: house.y }"
                :owner="house.owner"
                :ownerName="house.ownerName"
                :color="house.color"
            />
        </template>

        <template v-for="city in cities">
            <!-- [10,15] city: X at bottom-right -->
            <template v-if="city.slotCosts && city.slotCosts.length === 2 && city.slotCosts[0] === 10">
                <line
                    :key="city.name + '_x1'"
                    :x1="city.x + 10"
                    :y1="city.y + 10"
                    :x2="city.x + 19"
                    :y2="city.y + 19"
                    stroke="black"
                    stroke-width="3"
                    stroke-linecap="round"
                />
                <line
                    :key="city.name + '_x2'"
                    :x1="city.x + 19"
                    :y1="city.y + 10"
                    :x2="city.x + 10"
                    :y2="city.y + 19"
                    stroke="black"
                    stroke-width="3"
                    stroke-linecap="round"
                />
            </template>
            <!-- [15,20] city: X at top-middle -->
            <template v-if="city.slotCosts && city.slotCosts.length === 2 && city.slotCosts[0] === 15">
                <line
                    :key="city.name + '_x1'"
                    :x1="city.x - 5"
                    :y1="city.y - 21"
                    :x2="city.x + 5"
                    :y2="city.y - 11"
                    stroke="black"
                    stroke-width="3"
                    stroke-linecap="round"
                />
                <line
                    :key="city.name + '_x2'"
                    :x1="city.x + 5"
                    :y1="city.y - 21"
                    :x2="city.x - 5"
                    :y2="city.y - 11"
                    stroke="black"
                    stroke-width="3"
                    stroke-linecap="round"
                />
            </template>
        </template>

        <template v-if="!preferences.disableHelp">
            <template v-for="city in cities">
                <circle
                    v-if="canBuild(city)"
                    :key="city.name + '_circleHelp'"
                    :class="[{ canClick: canBuild(city) }]"
                    r="18"
                    :cx="city.x"
                    :cy="city.y"
                    fill="none"
                    stroke="blue"
                    stroke-width="4px"
                />
            </template>
        </template>
    </g>
</template>

<script lang="ts">
import type { GameState } from 'powergrid-engine';
import { Vue, Component, Prop, Inject } from 'vue-property-decorator';
import { House } from '../pieces';
import { Piece, Preferences } from '../../types/ui-data';
import { City, Connection, Polygon } from 'powergrid-engine/src/maps';

@Component({
    components: {
        House
    },
})
export default class Map extends Vue {
    @Prop() polygons?: Polygon[];
    @Prop() cities?: City[];
    @Prop() connections?: Connection[];
    @Prop() playerColors?: string[];
    @Prop() buildableCities?: string[];
    @Prop() devBackdrop?: { src: string; width: number; height: number; opacity?: number };

    @Inject() preferences!: Preferences;

    houses: Piece[] = [];

    createPieces(gameState: GameState) {
        this.houses = [];
        gameState.players.forEach((player, pi) => {
            player.cities.forEach((cityPiece) => {
                const city = gameState.map.cities.find((city) => city.name == cityPiece.name)!;
                let offsetX, offsetY;
                if (cityPiece.position == 0) {
                    offsetX = -6;
                    offsetY = -18;
                } else if (cityPiece.position == 1) {
                    offsetX = -15;
                    offsetY = -4;
                } else {
                    offsetX = 1;
                    offsetY = -4;
                }

                this.houses.push({
                    id: pi + '_' + cityPiece.name,
                    x: city.x + offsetX,
                    y: city.y + offsetY,
                    color: this.playerColors![pi],
                    owner: pi,
                });
            });
        });
    }

    getX1(connection) {
        const city = this.cities!.find((city) => city.name == connection.nodes[0])!;
        return city.x;
    }

    getY1(connection) {
        const city = this.cities!.find((city) => city.name == connection.nodes[0])!;
        return city.y;
    }

    getX2(connection) {
        const city = this.cities!.find((city) => city.name == connection.nodes[1])!;
        return city.x;
    }

    getY2(connection) {
        const city = this.cities!.find((city) => city.name == connection.nodes[1])!;
        return city.y;
    }

    canBuild(city: City) {
        return !!this.buildableCities!.find((cityName) => cityName == city.name);
    }

    build(city: City) {
        this.$emit('build', city);
    }

    onPickCoord(e: MouseEvent) {
        if (!this.devBackdrop) return;
        const g = e.currentTarget as SVGGElement;
        const ctm = g.getScreenCTM();
        if (!ctm) return;
        const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(ctm.inverse());
        // eslint-disable-next-line no-console
        console.log(`{ name: Cities.TODO, region: Regions.TODO, x: ${Math.round(pt.x)}, y: ${Math.round(pt.y)} },`);
    }
}
</script>
