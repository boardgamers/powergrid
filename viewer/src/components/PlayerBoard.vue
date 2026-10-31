<template>
    <g class="player-board">
        <rect
            width="350"
            :height="100 + (showAutoPass ? settingRowHeight : 0)"
            x="0"
            y="0"
            fill="gold"
            :stroke="color"
        />
        <rect width="350" height="25" x="0" y="0" :fill="color" />
        <foreignObject height="30" width="30" x="-30" y="-5">
            <img
                :src="avatar || `https://avatars.dicebear.com/api/pixel-art/${player.name}.svg`"
                width="100%"
                height="100%"
                style="border-radius: 50%"
            />
        </foreignObject>
        <image
            v-if="supporterBadge"
            :href="supporterBadge.url"
            x="5"
            y="4"
            width="17"
            height="17"
            :aria-label="supporterBadge.label"
        >
            <title>{{ supporterBadge.label }}</title>
        </image>
        <text
            :data-bgs-player="owner"
            style="pointer-events: all"
            tabindex="0"
            :x="supporterBadge ? 27 : 5"
            y="13"
            font-weight="600"
            :fill="colorText(color)"
        >
            {{ getPlayerName() }}
        </text>
        <text v-if="showMoney" x="250" y="13" font-weight="600" :fill="colorText(color)"
            >Money: ${{ player.money }}</text
        >

        <!-- Keep the full preference inside the viewer's own player card. -->
        <template v-if="showAutoPass">
            <g
                class="auction-auto-pass"
                :class="{ editable: !autoPassDisabled }"
                transform="translate(0, 100)"
                data-auction-auto-pass
                :role="autoPassPublic ? 'note' : 'checkbox'"
                :aria-checked="autoPassPublic ? undefined : String(autoPass)"
                :aria-disabled="autoPassDisabled ? 'true' : 'false'"
                :tabindex="autoPassPublic || autoPassDisabled ? -1 : 0"
                aria-label="Auto-pass if unaffordable"
                @click="!autoPassDisabled && $emit('toggleAutoPass')"
                @keydown.enter.prevent="!autoPassDisabled && $emit('toggleAutoPass')"
                @keydown.space.prevent="!autoPassDisabled && $emit('toggleAutoPass')"
            >
                <rect class="auto-pass-hit" width="350" :height="settingRowHeight" fill="transparent" />
                <path d="M0 0H350" stroke="#806b28" stroke-opacity="0.35" />
                <rect
                    x="10"
                    y="9"
                    width="18"
                    height="18"
                    rx="2"
                    :fill="autoPass ? '#304b3b' : '#f5f4e5'"
                    stroke="#304b3b"
                />
                <path v-if="autoPass" d="M14 18L18 22L24 14" fill="none" stroke="white" stroke-width="2" />
                <text x="37" y="18" fill="#24382b" style="font: 16px Arial, sans-serif; dominant-baseline: central"
                    >Auto-pass if unaffordable</text
                >
                <title>
                    {{
                        autoPassPublic
                            ? 'Money is public: players automatically pass auctions they cannot afford.'
                            : 'Automatically pass auctions you cannot afford. With hidden money, this can reveal that you cannot afford the bid. Applies after the next move.'
                    }}
                </title>
            </g>
        </template>

        <Card
            v-for="(powerPlant, i) in player.powerPlants"
            :key="'powerPlant_' + powerPlant.number"
            :targetState="{ x: cardX(i), y: 30 }"
            :owner="owner"
            :powerPlant="powerPlant"
            :canClick="canUse(powerPlant)"
            :activationState="activationState(powerPlant)"
            :data-plant-number="powerPlant.number"
            @click="powerPlantClick(powerPlant)"
        />

        <!-- Australia: mark uranium mines (they sell uranium instead of powering
             cities, and don't count toward the 3-plant limit) with a green frame
             and a uranium badge. -->
        <template v-for="(powerPlant, i) in player.powerPlants">
            <g v-if="isMine(powerPlant)" :key="'mine_' + powerPlant.number">
                <rect
                    :x="cardX(i)"
                    y="30"
                    width="60"
                    height="40"
                    fill="none"
                    stroke="#2e8b3d"
                    stroke-width="3px"
                    rx="3px"
                />
                <rect :x="cardX(i) + 42" y="28" width="18" height="19" rx="3" fill="#f4e5a8" stroke="#806b28" />
                <Uranium
                    :pieceId="'uraniumMineBadge_' + powerPlant.number"
                    :targetState="{ x: cardX(i) + 41, y: 29 }"
                />
            </g>
        </template>

        <template>
            <template v-for="(powerPlant, i) in player.powerPlants">
                <rect
                    v-if="canUse(powerPlant)"
                    :key="i + '_' + i + '_helper'"
                    :x="cardX(i)"
                    :y="30"
                    width="60"
                    height="40"
                    fill="none"
                    :stroke="player.availableMoves && player.availableMoves.DiscardPowerPlant ? '#c62828' : 'blue'"
                    stroke-width="4px"
                    rx="2px"
                />
            </template>
        </template>

        <g v-if="canClickResources">
            <rect
                v-if="canClickResource('coal')"
                width="30"
                height="30"
                x="0"
                y="71"
                fill="none"
                stroke="blue"
                stroke-width="2px"
                rx="2px"
            />
            <rect
                v-if="canClickResource('oil')"
                width="30"
                height="30"
                x="70"
                y="71"
                fill="none"
                stroke="blue"
                stroke-width="2px"
                rx="2px"
            />
            <rect
                v-if="canClickResource('garbage')"
                width="30"
                height="30"
                x="140"
                y="71"
                fill="none"
                stroke="blue"
                stroke-width="2px"
                rx="2px"
            />
        </g>

        <Coal
            :pieceId="'Coal' + player.id"
            :targetState="{ x: 5, y: 76 }"
            :canClick="canClickResource('coal')"
            @click="clickResource('coal')"
        />
        <text text-anchor="middle" x="40" y="85" fill="black">{{ player.coalLeft }}</text>

        <Oil
            :pieceId="'Oil' + player.id"
            :targetState="{ x: 75, y: 76 }"
            :canClick="canClickResource('oil')"
            @click="clickResource('oil')"
        />
        <text text-anchor="middle" x="110" y="85" fill="black">{{ player.oilLeft }}</text>

        <Garbage
            :pieceId="'Garbage' + player.id"
            :targetState="{ x: 145, y: 76 }"
            :canClick="canClickResource('garbage')"
            @click="clickResource('garbage')"
        />
        <text text-anchor="middle" x="180" y="85" fill="black">{{ player.garbageLeft }}</text>

        <Uranium :pieceId="'Uranium' + player.id" :targetState="{ x: 215, y: 76 }" />
        <text text-anchor="middle" x="250" y="85" fill="black">{{ player.uraniumLeft }}</text>

        <!-- Time this player has spent on the clock. Ticks live while it is their
             turn; sits in the free space right of the resource counters. -->
        <text
            text-anchor="end"
            x="345"
            y="85"
            fill="black"
            :font-weight="isCurrentPlayer ? 700 : 400"
            style="font-size: 13px"
        >
            {{ timeUsed }}
        </text>
    </g>
</template>
<script lang="ts">
import { playerSymbol } from "../player-colors";
import { colorText } from '../player-colors';
import { MoveName, Player } from 'powergrid-engine';
import { Phase, playerTimeUsed, PowerPlant, PowerPlantType, ResourceType } from 'powergrid-engine/src/gamestate';
import { Vue, Component, Prop, Inject } from 'vue-property-decorator';
import { Preferences } from '../types/ui-data';
import { formatDuration } from '../util/time';
import { PLAYER_SETTING_ROW_HEIGHT } from '../util/board-layout';
import { Coal, Oil, Garbage, Uranium, Card } from './pieces';

@Component({
    components: {
        Coal,
        Oil,
        Garbage,
        Uranium,
        Card
    }
})
export default class PlayerBoard extends Vue {
    colorText = colorText;
    @Prop() color?: string;
    @Prop() avatar?: string;
    @Prop() player!: Player;
    @Prop() isCurrentPlayer?: boolean;
    @Prop() owner?: number;
    @Prop() ended?: boolean;
    @Prop() isPlayer?: boolean;
    @Prop() ranking?: number;
    @Prop() showMoney?: boolean;
    @Prop() showBid?: boolean;
    @Prop() phase?: Phase;
    // Australia: uranium plants are "mines" — flag so the hand marks them distinctly.
    @Prop() isAustralia?: boolean;
    @Prop({ default: false }) showAutoPass!: boolean;
    @Prop({ default: false }) autoPass!: boolean;
    @Prop({ default: false }) autoPassPublic!: boolean;
    @Prop({ default: true }) autoPassDisabled!: boolean;

    settingRowHeight = PLAYER_SETTING_ROW_HEIGHT;

    @Inject() preferences!: Preferences;

    get supporterBadge() {
        return this.owner !== undefined && this.preferences.bgs?.players?.[this.owner]?.pro
            ? this.preferences.bgs.supporterBadge
            : undefined;
    }

    powerPlantClicked?: PowerPlant;

    // Ticks the live clock. Kept in this component rather than in Game so the
    // per-second update only re-renders the player boards, not the whole board SVG.
    now = Date.now();
    private clockTimer?: number;

    mounted() {
        this.clockTimer = window.setInterval(() => (this.now = Date.now()), 1000);
    }

    beforeDestroy() {
        if (this.clockTimer != undefined) {
            window.clearInterval(this.clockTimer);
        }
    }

    // Total time this player has been on the clock, counting the stretch currently
    // running so the active player's timer visibly ticks up.
    get timeUsed(): string {
        return formatDuration(playerTimeUsed(this.player, this.now));
    }

    // Horizontal position of the i-th power-plant card. Spacing compresses as the
    // hand grows so Australia's mines (which don't count toward the 3-plant limit,
    // so a player can hold many cards) stay on the board instead of overflowing
    // off the right edge. Non-Australia hands never exceed 4, so they are unaffected.
    cardX(i: number): number {
        const n = this.player.powerPlants.length;
        if (n < 5) return 20 + 80 * i;
        return 5 + Math.min(70, 280 / (n - 1)) * i;
    }

    isMine(powerPlant: PowerPlant): boolean {
        return this.isAustralia === true && powerPlant.type === PowerPlantType.Uranium;
    }

    getPlayerName() {
        let name = '';
        if (this.isCurrentPlayer) {
            name += '• ';
        }

        if (this.preferences.colorBlind && this.owner !== undefined) name += `${playerSymbol(this.owner, this.preferences)} · `;
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
        } else if (this.player.bid && !this.isCurrentPlayer && this.showBid) {
            name += ' (Bid: $' + this.player.bid + ')';
        }

        return name;
    }

    activationState(plant: PowerPlant) {
        if (!this.isPlayer || this.phase !== Phase.Bureaucracy || this.isMine(plant)) return undefined;
        if (!this.player.powerPlantsNotUsed.includes(plant.number)) return 'used';
        const fuel = [this.player.coalLeft, this.player.oilLeft, this.player.garbageLeft,
            this.player.uraniumLeft, this.player.coalLeft + this.player.oilLeft];
        fuel[PowerPlantType.GarbageOilHybrid] = this.player.garbageLeft + this.player.oilLeft;
        if (plant.cost > 0 && fuel[plant.type] < plant.cost) return 'unavailable';
        return this.canUse(plant) ? 'ready' : 'idle';
    }

    canUse(powerPlant: PowerPlant) {
        if (!this.isCurrentPlayer) return false;
        const moves = this.player.availableMoves;
        if (moves?.DiscardPowerPlant) return moves.DiscardPowerPlant.includes(powerPlant.number);
        return this.player.resourcesUsed.length === 0 &&
            !!moves?.UsePowerPlant?.some((move) => move.powerPlant === powerPlant.number);
    }

    // The fuel a hybrid plant can burn besides oil: coal for the standard hybrid,
    // garbage for the alternate deck's garbage/oil hybrid. Undefined for other plants.
    hybridFuel(powerPlant: PowerPlant): ResourceType.Coal | ResourceType.Garbage | undefined {
        if (powerPlant.type == PowerPlantType.Hybrid) return ResourceType.Coal;
        if (powerPlant.type == PowerPlantType.GarbageOilHybrid) return ResourceType.Garbage;
        return undefined;
    }

    powerPlantClick(powerPlant: PowerPlant) {
        const other = this.hybridFuel(powerPlant);
        if (this.phase == Phase.Bureaucracy && other) {
            const otherLeft = other == ResourceType.Coal ? this.player.coalLeft : this.player.garbageLeft;
            if (
                otherLeft == 0 ||
                this.player.oilLeft == 0 ||
                otherLeft + this.player.oilLeft == powerPlant.cost
            ) {
                this.player.resourcesUsed = Array(Math.min(powerPlant.cost, otherLeft))
                    .fill(other)
                    .concat(
                        Array(powerPlant.cost - Math.min(powerPlant.cost, otherLeft)).fill(ResourceType.Oil)
                    );
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
        return (
            (this.player.availableMoves && this.player.availableMoves['DiscardResources']) ||
            this.player.resourcesUsed.some(r => r == null)
        );
    }

    // Whether this resource can be clicked: offered as a discard, or a fuel of the
    // hybrid plant whose resources are being chosen.
    canClickResource(resourceType: ResourceType) {
        const discards = this.player.availableMoves?.DiscardResources;
        if (discards) {
            // The engine only handles garbage discards for garbage/oil hybrid owners.
            if (resourceType == ResourceType.Garbage && !this.player.garbageOilHybridCapacity) return false;
            return discards.includes(resourceType);
        }
        if (!this.player.resourcesUsed.some(r => r == null)) return false;
        // Without the clicked plant (not expected), fall back to the coal/oil hybrid.
        const other = this.powerPlantClicked ? this.hybridFuel(this.powerPlantClicked) : ResourceType.Coal;
        return resourceType == ResourceType.Oil || resourceType == other;
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
            } else if (resourceType == 'garbage') {
                this.player.garbageLeft--;
            }

            if (!this.player.resourcesUsed.some(r => r == null)) {
                this.$emit('powerPlantClick', this.powerPlantClicked);
            }
        }
    }
}
</script>
<style scoped>
.auction-auto-pass.editable {
    cursor: pointer;
}
.auction-auto-pass.editable:hover .auto-pass-hit {
    fill: #ffffff30;
}
.auction-auto-pass:focus {
    outline: none;
}
.auction-auto-pass:focus-visible .auto-pass-hit {
    stroke: currentColor;
    stroke-width: 2;
}
</style>
