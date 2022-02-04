<template>
    <g>
        <text x="10" y="14" font-weight="600" fill="black">Power Plant Deck:</text>
        <template v-if="cardsLeft > 0">
            <rect
                v-for="index in cardsLeft"
                :key="'card' + index"
                :x="35 + index / 5"
                :y="38 - index / 10"
                width="60"
                height="40"
                fill="gray"
                stroke="black"
                stroke-width="2"
                rx="4"
            />
            <rect
                :x="35 + cardsLeft / 5"
                :y="38 - cardsLeft / 10"
                width="60"
                height="40"
                :fill="nextCardWeak ? 'gray' : 'lightgray'"
                stroke="black"
                stroke-width="2"
                rx="4"
            >
                <title>{{ cardsLeft }} cards left{{ nextCardWeak ? ', next is an initial plant' : '' }}</title>
            </rect>
        </template>

        <text x="165" y="14" font-weight="600" fill="black">Actual Market:</text>
        <template v-for="(card, i) in actualMarketCards">
            <Card
                :key="card.id"
                :targetState="{ x: card.x, y: card.y }"
                :powerPlant="card.powerPlant"
                :canClick="chooseablePowerPlants && chooseablePowerPlants.includes(card.powerPlant.number)"
                :hasDiscount="plantDiscountActive && i == 0"
                @click="choosePowerPlant(card.powerPlant)"
            />
        </template>

        <template v-if="futureMarketCards.length > 0">
            <text x="165" y="80" font-weight="600" fill="black">Future Market:</text>
            <template v-for="card in futureMarketCards">
                <Card :key="card.id" :targetState="{ x: card.x, y: card.y }" :powerPlant="card.powerPlant" />
            </template>
        </template>

        <template v-if="chosenPowerPlant">
            <text x="430" y="14" font-weight="600" fill="black">Current Auction:</text>
            <Card
                :key="chosenPowerPlant.id"
                :targetState="{ x: chosenPowerPlant.x, y: chosenPowerPlant.y }"
                :powerPlant="chosenPowerPlant.powerPlant"
            />
            <Calculator
                v-if="canBid"
                transform="translate(430, 80)"
                :minValue="minBid"
                :maxValue="maxBid"
                @bid="bid($event)"
            />
        </template>

        <template v-if="!preferences.disableHelp">
            <g v-if="canChoose">
                <rect
                    v-if="futureMarketCards.length > 0"
                    x="160"
                    y="5"
                    width="265"
                    height="65"
                    fill="none"
                    stroke="blue"
                    stroke-width="2px"
                    rx="2px"
                />

                <rect
                    v-else
                    x="160"
                    y="5"
                    width="200"
                    height="120"
                    fill="none"
                    stroke="blue"
                    stroke-width="2px"
                    rx="2px"
                />
            </g>
        </template>
    </g>
</template>

<script lang="ts">
import type { GameState } from 'powergrid-engine';
import { PowerPlant } from 'powergrid-engine/src/gamestate';
import { Vue, Component, Prop, Inject } from 'vue-property-decorator';
import { Card } from './../pieces';
import { Piece, Preferences } from '../../types/ui-data';
import Calculator from './../Calculator.vue';

@Component({
    components: {
        Card,
        Calculator
    },
})
export default class PowerPlantMarket extends Vue {
    @Prop() cardsLeft?: number;
    @Prop() nextCardWeak?: boolean;
    @Prop() plantDiscountActive?: boolean;
    @Prop() canBid?: boolean;
    @Prop() canChoose?: boolean;
    @Prop() chooseablePowerPlants?: number[];
    @Prop() minBid?: number;
    @Prop() maxBid?: number;

    @Inject() preferences!: Preferences;

    actualMarketCards: Piece[] = [];
    futureMarketCards: Piece[] = [];
    chosenPowerPlant: Piece | null = null;

    createPieces(gameState: GameState) {
        this.actualMarketCards = [];
        gameState.actualMarket.forEach((card, i) => {
            if (gameState.futureMarket.length > 0) {
                if (card.number != gameState.chosenPowerPlant?.number) {
                    this.actualMarketCards.push({
                        id: 'actual_' + i,
                        x: 165 + i * 65,
                        y: 24,
                        powerPlant: card
                    });
                }
            } else {
                if (card.number != gameState.chosenPowerPlant?.number) {
                    this.actualMarketCards.push({
                        id: 'actual_' + i,
                        x: 165 + (i % 3) * 65,
                        y: i < 3 ? 24 : 80,
                        powerPlant: card
                    });
                }
            }
        });

        this.futureMarketCards = [];
        gameState.futureMarket.forEach((card, i) => {
            if (card.number != gameState.chosenPowerPlant?.number) {
                this.futureMarketCards.push({
                    id: 'future_' + i,
                    x: 165 + i * 65,
                    y: 90,
                    powerPlant: card
                });
            }
        });

        if (gameState.chosenPowerPlant) {
            this.chosenPowerPlant = {
                id: 'chosen',
                x: 460,
                y: 30,
                powerPlant: gameState.chosenPowerPlant
            };
        } else {
            this.chosenPowerPlant = null;
        }
    }

    choosePowerPlant(powerPlant: PowerPlant) {
        this.$emit('choosePowerPlant', powerPlant);
    }

    bid(bid: number) {
        this.$emit('bid', bid);
    }
}
</script>
