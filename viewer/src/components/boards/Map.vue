<template>
    <g>
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
}
</script>
