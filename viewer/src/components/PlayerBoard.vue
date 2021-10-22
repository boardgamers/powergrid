<template>
    <g class="player-board">
        <rect width="350" height="100" x="0" y="0" fill="gold" :stroke="color" />
        <rect width="350" height="25" x="0" y="0" :fill="color" />
        <text x="5" y="13" font-weight="600" fill="black" :text-decoration="isCurrentPlayer ? 'underline' : ''">
            {{ getPlayerName() }}
        </text>
        <text v-if="isPlayer || ended" x="250" y="13" font-weight="600" fill="black">Money: ${{ player.money }}</text>

        <Card
            v-for="(powerPlant, i) in player.powerPlants"
            :key="'powerPlant_' + powerPlant.number"
            :targetState="{ x: player.powerPlants.length < 5 ? 20 + 80 * i : 5 + 70 * i, y: 30 }"
            :owner="owner"
            :powerPlant="powerPlant"
            :canClick="canUse(powerPlant)"
            @click="powerPlantClick(powerPlant)"
        />

        <g v-if="canClickResources">
            <rect width="30" height="30" x="0" y="71" fill="none" stroke="blue" stroke-width="2px" rx="2px" />
            <rect width="30" height="30" x="70" y="71" fill="none" stroke="blue" stroke-width="2px" rx="2px" />
        </g>

        <Coal
            :pieceId="'Coal' + player.id"
            :targetState="{ x: 5, y: 76 }"
            :canClick="canClickResources"
            @click="clickResource('coal')"
        />
        <text text-anchor="middle" x="40" y="85" fill="black">{{ player.coalLeft }}</text>

        <Oil
            :pieceId="'Oil' + player.id"
            :targetState="{ x: 75, y: 76 }"
            :canClick="canClickResources"
            @click="clickResource('oil')"
        />
        <text text-anchor="middle" x="110" y="85" fill="black">{{ player.oilLeft }}</text>

        <Garbage :pieceId="'Garbage' + player.id" :targetState="{ x: 145, y: 76 }" />
        <text text-anchor="middle" x="180" y="85" fill="black">{{ player.garbageLeft }}</text>

        <Uranium :pieceId="'Uranium' + player.id" :targetState="{ x: 215, y: 76 }" />
        <text text-anchor="middle" x="250" y="85" fill="black">{{ player.uraniumLeft }}</text>
    </g>
</template>
<script lang="ts">
import { MoveName, Player } from 'powergrid-engine';
import { PowerPlant, PowerPlantType, ResourceType } from 'powergrid-engine/src/gamestate';
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

    @Prop()
    ranking?: number;

    powerPlantClicked?: PowerPlant;

    getPlayerName() {
        let name = '';
        if (this.isCurrentPlayer) {
            name += '• ';
        }

        name += this.player.name;

        if (this.ended) {
            switch (this.ranking) {
                case 1:
                    name += ' (1st)';
                    break;
                case 2:
                    name += ' (2nd)';
                    break;
                case 3:
                    name += ' (3rd)';
                    break;
                case 4:
                case 5:
                case 6:
                    name += ` (${this.ranking}th)`;
                    break;
            }
        } else if (this.player.skipAuction) {
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
            if (!this.player.powerPlantsNotUsed.includes(powerPlant.number) || this.player.resourcesUsed.length > 0) {
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

    powerPlantClick(powerPlant: PowerPlant) {
        if (powerPlant.type == PowerPlantType.Hybrid) {
            if (this.player.coalLeft == 0 || this.player.oilLeft == 0 || this.player.coalLeft + this.player.oilLeft == powerPlant.cost) {
                this.player.resourcesUsed = Array(Math.min(powerPlant.cost, this.player.coalLeft)).fill(ResourceType.Coal)
                    .concat(Array(powerPlant.cost - Math.min(powerPlant.cost, this.player.coalLeft)).fill(ResourceType.Oil));
                this.$emit('powerPlantClick', powerPlant);
            } else {
                this.powerPlantClicked = powerPlant;
                this.player.resourcesUsed = Array(powerPlant.cost).fill(null);
            }
        } else {
            this.$emit('powerPlantClick', powerPlant);
        }
    }

    get canClickResources() {
        return this.player.availableMoves && this.player.availableMoves['DiscardResources'] || this.player.resourcesUsed.some(r => r == null);
    }

    clickResource(resourceType) {
        if (this.player.availableMoves && this.player.availableMoves['DiscardResources']) {
            this.$emit('discardResource', resourceType);
        } else if (this.player.resourcesUsed.some(r => r == null)) {
            const index = this.player.resourcesUsed.findIndex(r => r == null)!;
            this.player.resourcesUsed[index] = resourceType;

            if (resourceType == 'coal') {
                this.player.coalLeft--;
            } else if (resourceType == 'oil') {
                this.player.oilLeft--;
            }

            if (!this.player.resourcesUsed.some(r => r == null)) {
                this.$emit('powerPlantClick', this.powerPlantClicked);
            }
        }
    }
}
</script>
