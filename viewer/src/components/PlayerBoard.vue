<template>
    <g class="player-board">
        <rect width="350" height="100" x="0" y="0" fill="gold" :stroke="color" />
        <rect width="350" height="25" x="0" y="0" :fill="color" />
        <text x="5" y="13" font-weight="600" fill="black" :text-decoration="isCurrentPlayer ? 'underline' : ''">{{
            getPlayerName()
        }}</text>
        <text v-if="isPlayer || ended" x="250" y="13" font-weight="600" fill="black">Money: ${{ player.money }}</text>

        <Card
            v-for="(powerPlant, i) in player.powerPlants"
            :key="'powerPlant_' + powerPlant.number"
            :targetState="{ x: 20 + 80 * i, y: 30 }"
            :owner="owner"
            :powerPlant="powerPlant"
            :canClick="canUse(powerPlant)"
            @click="$emit('powerPlantClick', powerPlant)"
        />

        <Coal :pieceId="'Coal' + player.id" :targetState="{ x: 5, y: 76 }" />
        <text text-anchor="middle" x="40" y="85" fill="black">{{ player.coalLeft }}</text>

        <Oil :pieceId="'Oil' + player.id" :targetState="{ x: 75, y: 76 }" />
        <text text-anchor="middle" x="110" y="85" fill="black">{{ player.oilLeft }}</text>

        <Garbage :pieceId="'Garbage' + player.id" :targetState="{ x: 145, y: 76 }" />
        <text text-anchor="middle" x="180" y="85" fill="black">{{ player.garbageLeft }}</text>

        <Uranium :pieceId="'Uranium' + player.id" :targetState="{ x: 215, y: 76 }" />
        <text text-anchor="middle" x="250" y="85" fill="black">{{ player.uraniumLeft }}</text>
    </g>
</template>
<script lang="ts">
import { MoveName, Player } from 'powergrid-engine';
import { PowerPlantType } from 'powergrid-engine/src/gamestate';
import { Vue, Component, Prop } from 'vue-property-decorator';
import { Coal, Oil, Garbage, Uranium, Card } from './pieces';

@Component({
    components: {
        Coal, Oil, Garbage, Uranium, Card
    },
})
export default class PlayerBoard extends Vue {
    @Prop()
    color?: string;

    @Prop()
    player!: Player;

    @Prop()
    isCurrentPlayer?: boolean;

    @Prop()
    owner?: number;

    @Prop()
    ended?: boolean;

    @Prop()
    isPlayer?: boolean;

    getPlayerName() {
        let name = '';
        if (this.isCurrentPlayer) {
            name += '• ';
        }

        name += this.player.name;

        if (this.player.skipAuction) {
            name += ' (Skipping)';
        } else if (this.player.passed) {
            name += ' (Passed)';
        } else if (this.player.bid && !this.isCurrentPlayer) {
            name += ' (Bid: $' + this.player.bid + ')';
        }

        return name;
    }

    canUse(powerPlant) {
        if (this.player.availableMoves?.[MoveName.DiscardPowerPlant]) {
            return true;
        } else {
            if (!this.player.powerPlantsNotUsed.includes(powerPlant.number)) {
                return false;
            }

            switch (powerPlant.type) {
                case PowerPlantType.Coal: {
                    return this.player.coalLeft >= powerPlant.cost;
                }

                case PowerPlantType.Oil: {
                    return this.player.oilLeft >= powerPlant.cost;
                }

                case PowerPlantType.Garbage: {
                    return this.player.garbageLeft >= powerPlant.cost;
                }

                case PowerPlantType.Uranium: {
                    return this.player.uraniumLeft >= powerPlant.cost;
                }

                case PowerPlantType.Hybrid: {
                    return this.player.coalLeft + this.player.oilLeft >= powerPlant.cost;
                }

                case PowerPlantType.Wind:
                case PowerPlantType.Nuclear:
                    return this.player.coalLeft + this.player.oilLeft >= powerPlant.cost;
            }
        }
    }
}
</script>
