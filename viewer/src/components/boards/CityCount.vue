<template>
    <g>
        <rect width="730" height="50" x="10" y="10" rx="3" fill="goldenrod" />
        <template v-for="index in 21">
            <rect
                :key="'playerCityCount' + index"
                width="28"
                height="38"
                :x="46 + 33 * (index - 1)"
                y="16"
                rx="2"
                fill="darkgoldenrod"
                :stroke="index == citiesToStep2 || index == citiesToEndGame ? '#916a08' : 'darkgoldenrod'"
                stroke-width="2px"
            />
            <text
                :key="'playerCityCountText' + index"
                text-anchor="middle"
                style="font-size: 24px; font-family: monospace"
                letter-spacing="-2"
                :x="59 + 33 * (index - 1)"
                y="35"
                fill="gold"
            >
                {{ index }}
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
    </g>
</template>

<script lang="ts">
import type { GameState } from 'powergrid-engine';
import { Vue, Component, Prop } from 'vue-property-decorator';
import { House } from '../pieces';
import { Piece } from '../../types/ui-data';

@Component({
    components: {
        House
    },
})
export default class CityCount extends Vue {
    @Prop() citiesToStep2?: number;
    @Prop() citiesToEndGame?: number;
    @Prop() playerColors?: string[];

    houses: Piece[] = [];

    createPieces(gameState: GameState) {
        this.houses = [];
        const adjustCityCount: number[][] = [];
        for (let i = 0; i < 22; i++) adjustCityCount[i] = [];

        gameState.players.forEach((player, pi) => adjustCityCount[player.cities.length].push(pi));
        gameState.players.forEach((player, pi) => {
            let x = (adjustCityCount[player.cities.length].length == 1 ? 23 : 20) + 33 * player.cities.length;
            x += (adjustCityCount[player.cities.length].indexOf(pi) % 2) * 6;

            this.houses.push({
                id: pi + '_cityCount',
                x: x,
                y:
                    15 +
                    (adjustCityCount[player.cities.length].indexOf(pi) * 30) /
                    adjustCityCount[player.cities.length].length,
                color: this.playerColors![pi],
                owner: pi,
            });
        });
    }
}
</script>
