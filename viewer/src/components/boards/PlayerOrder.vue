<template>
    <g>
        <rect x="10" y="10" width="185" height="40" rx="3" fill="goldenrod" />
        <template v-for="index in 6">
            <rect
                :key="'playerOrder' + index"
                :x="15 + 30 * (index - 1)"
                y="15"
                width="24"
                height="30"
                rx="2"
                fill="darkgoldenrod"
            />
            <text
                :key="'playerOrderText' + index"
                text-anchor="middle"
                style="font-size: 32px; font-family: monospace"
                :x="27 + 30 * (index - 1)"
                y="30"
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
export default class PlayerOrder extends Vue {
    @Prop() playerColors?: string[];

    houses: Piece[] = [];

    createPieces(gameState: GameState) {
        this.houses = [];
        gameState.playerOrder.forEach((p, i) => {
            this.houses.push({
                id: p + '_order',
                x: 20 + 30 * i,
                y: 22,
                color: this.playerColors![p],
                owner: p,
                ownerName: gameState.players[p].name
            });
        });
    }
}
</script>
