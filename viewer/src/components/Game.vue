<template>
    <div class="game">
        <div class="statusBar">
            {{ getStatusMessage() }}
        </div>
        <audio id="piece-drop" preload="none">
            <source src="../audio/piece-drop.mp3" type="audio/mpeg" />
        </audio>
        <audio id="notification" preload="none">
            <source src="../audio/notification.mp3" type="audio/mpeg" />
            <source src="../audio/notification.ogg" type="audio/ogg" />
        </audio>
        <svg id="scene" viewBox="0 0 1500 800" height="700">
            <rect width="100%" height="100%" x="0" y="0" fill="yellowgreen" />

            <rect width="185" height="40" x="10" y="10" rx="3" fill="goldenrod" />
            <template v-for="index in 6">
                <rect
                    :key="'playerOrder' + index"
                    width="25"
                    height="30"
                    :x="15 + 30 * (index - 1)"
                    y="15"
                    rx="2"
                    fill="darkgoldenrod"
                />
                <text
                    :key="'playerOrderText' + index"
                    text-anchor="middle"
                    style="font-size: 32px; font-family: monospace"
                    :x="28 + 30 * (index - 1)"
                    y="30"
                    fill="gold"
                >
                    {{ index }}
                </text>
            </template>

            <rect width="730" height="50" x="215" y="10" rx="3" fill="goldenrod" />
            <template v-for="index in 21">
                <rect
                    :key="'playerCityCount' + index"
                    width="30"
                    height="40"
                    :x="250 + 33 * (index - 1)"
                    y="15"
                    rx="2"
                    fill="darkgoldenrod"
                />
                <text
                    :key="'playerCityCountText' + index"
                    text-anchor="middle"
                    style="font-size: 24px; font-family: monospace"
                    letter-spacing="-3"
                    :text-decoration="G && (index == G.citiesToStep2 || index == G.citiesToEndGame) ? 'underline' : ''"
                    :x="265 + 33 * (index - 1)"
                    y="35"
                    fill="gold"
                >
                    {{ index }}
                </text>
            </template>

            <rect width="760" height="80" x="20" y="700" rx="3" fill="goldenrod" />
            <template v-for="index in 8">
                <rect
                    :key="'resources' + index"
                    width="70"
                    height="70"
                    :x="25 + 85 * (index - 1)"
                    y="705"
                    rx="2"
                    fill="darkgoldenrod"
                />
                <circle :key="'resourcesCircle' + index" r="10" :cx="92 + 85 * (index - 1)" cy="708" fill="yellow" />
                <text
                    :key="'resourcesText' + index"
                    text-anchor="middle"
                    style="font-size: 16px; font-family: monospace"
                    :x="92 + 85 * (index - 1)"
                    y="708"
                    fill="darkgoldenrod"
                >
                    {{ index }}
                </text>
                <g :key="'lines' + index">
                    <line
                        :x1="25 + 85 * (index - 1)"
                        y1="728"
                        :x2="95 + 85 * (index - 1)"
                        y2="728"
                        stroke="goldenrod"
                    />
                    <line
                        :x1="25 + 85 * (index - 1)"
                        y1="752"
                        :x2="95 + 85 * (index - 1)"
                        y2="752"
                        stroke="goldenrod"
                    />

                    <line
                        :x1="48 + 85 * (index - 1)"
                        y1="700"
                        :x2="48 + 85 * (index - 1)"
                        y2="728"
                        stroke="goldenrod"
                    />
                    <line
                        :x1="72 + 85 * (index - 1)"
                        y1="700"
                        :x2="72 + 85 * (index - 1)"
                        y2="728"
                        stroke="goldenrod"
                    />
                    <line
                        :x1="42 + 85 * (index - 1)"
                        y1="728"
                        :x2="42 + 85 * (index - 1)"
                        y2="752"
                        stroke="goldenrod"
                    />
                    <line
                        :x1="58 + 85 * (index - 1)"
                        y1="728"
                        :x2="58 + 85 * (index - 1)"
                        y2="752"
                        stroke="goldenrod"
                    />
                    <line
                        :x1="74 + 85 * (index - 1)"
                        y1="728"
                        :x2="74 + 85 * (index - 1)"
                        y2="752"
                        stroke="goldenrod"
                    />
                    <line
                        :x1="48 + 85 * (index - 1)"
                        y1="752"
                        :x2="48 + 85 * (index - 1)"
                        y2="780"
                        stroke="goldenrod"
                    />
                    <line
                        :x1="72 + 85 * (index - 1)"
                        y1="752"
                        :x2="72 + 85 * (index - 1)"
                        y2="780"
                        stroke="goldenrod"
                    />
                </g>
            </template>

            <rect width="30" height="30" x="705" y="705" rx="2" fill="darkgoldenrod" />
            <circle r="10" cx="732" cy="708" fill="yellow" />
            <text
                text-anchor="middle"
                style="font-size: 12px; font-family: monospace"
                x="732"
                y="708"
                fill="darkgoldenrod"
            >
                10
            </text>

            <rect width="30" height="30" x="745" y="705" rx="2" fill="darkgoldenrod" />
            <circle r="10" cx="772" cy="708" fill="yellow" />
            <text
                text-anchor="middle"
                style="font-size: 12px; font-family: monospace"
                x="772"
                y="708"
                fill="darkgoldenrod"
            >
                12
            </text>

            <rect width="30" height="30" x="705" y="745" rx="2" fill="darkgoldenrod" />
            <circle r="10" cx="732" cy="748" fill="yellow" />
            <text
                text-anchor="middle"
                style="font-size: 12px; font-family: monospace"
                x="732"
                y="748"
                fill="darkgoldenrod"
            >
                14
            </text>

            <rect width="30" height="30" x="745" y="745" rx="2" fill="darkgoldenrod" />
            <circle r="10" cx="772" cy="748" fill="yellow" />
            <text
                text-anchor="middle"
                style="font-size: 12px; font-family: monospace"
                x="772"
                y="748"
                fill="darkgoldenrod"
            >
                16
            </text>

            <text x="955" y="14" font-weight="600" fill="black">Actual Market:</text>
            <text v-if="G && G.step < 3" x="955" y="80" font-weight="600" fill="black">Future Market:</text>

            <template v-if="G">
                <template v-if="gameEnded(G)">
                    <Button
                        :transform="`translate(140, 580)`"
                        :width="130"
                        :text="'Final Score'"
                        @click="endScoreVisible = true"
                    />
                </template>
                <template v-else>
                    <text x="30" y="580" font-weight="600" fill="black" style="font-size: 32px">
                        Step: {{ G.step }}
                    </text>
                    <text x="30" y="620" font-weight="600" fill="black" style="font-size: 32px">
                        Phase: {{ G.phase }}
                    </text>
                    <text x="30" y="680" font-weight="600" fill="black" style="font-size: 24px">
                        Resource Resupply: {{ G.resourceResupply }}
                    </text>
                </template>
            </template>

            <PassButton transform="translate(1355, 15)" :enabled="canPass()" @click="pass()" />
            <UndoButton transform="translate(1355, 56)" :enabled="canUndo()" @click="undo()" />
            <LogButton transform="translate(1355, 97)" @click="showLog()" />
            <SoundButton transform="translate(1450, 25)" :isOn="preferences.sound" @click="toggleSound()" />
            <HelpButton transform="translate(1450, 80)" :isOn="!preferences.disableHelp" @click="toggleHelp()" />

            <template v-if="G">
                <template v-if="G.phase == 'Auction' && G.chosenPowerPlant">
                    <text x="1220" y="14" font-weight="600" fill="black">Current Auction:</text>
                    <Calculator
                        v-if="canBid()"
                        transform="translate(1220, 80)"
                        :minValue="G.currentBid + 1 || G.chosenPowerPlant.number"
                        :maxValue="G.players[player].money"
                        @bid="bid($event)"
                    />
                </template>

                <template v-for="city in G.map.cities">
                    <circle
                        :key="city.name + '_region'"
                        r="25"
                        :cx="city.x"
                        :cy="city.y - 30"
                        :fill="city.region"
                        stroke="black"
                    >
                        <title>{{ city.name }}</title>
                    </circle>
                    <circle
                        :key="city.name + '_circle'"
                        r="20"
                        :cx="city.x"
                        :cy="city.y - 30"
                        fill="gray"
                        stroke="black"
                    >
                        <title>{{ city.name }}</title>
                    </circle>
                </template>

                <template v-for="connection in G.map.connections">
                    <line
                        :key="connection.from + '_' + connection.to + '_line1'"
                        :x1="getX1(connection)"
                        :y1="getY1(connection) - 30"
                        :x2="getX2(connection)"
                        :y2="getY2(connection) - 30"
                        stroke-width="10"
                        stroke="black"
                    />
                    <line
                        :key="connection.from + '_' + connection.to + '_line2'"
                        :x1="getX1(connection)"
                        :y1="getY1(connection) - 30"
                        :x2="getX2(connection)"
                        :y2="getY2(connection) - 30"
                        stroke-width="9"
                        stroke="gray"
                    />
                </template>

                <template v-for="city in G.map.cities">
                    <circle
                        :key="city.name + '_circle2'"
                        :class="[{ canClick: canBuild(city) }]"
                        r="20"
                        :cx="city.x"
                        :cy="city.y - 30"
                        fill="gray"
                        @click="canBuild(city) && build(city)"
                    >
                        <title>{{ city.name }}</title>
                    </circle>
                </template>

                <template v-for="connection in G.map.connections">
                    <circle
                        v-if="connection.cost > 0"
                        :key="connection.from + '_' + connection.to + '_border'"
                        stroke="black"
                        :r="10 + (connection.cost * 10) / 28"
                        :cx="(getX1(connection) + getX2(connection)) / 2"
                        :cy="(getY1(connection) + getY2(connection) - 60) / 2"
                        :fill="connection.cost > 15 ? 'gold' : connection.cost > 10 ? 'lightgray' : 'tan'"
                    />
                    <circle
                        v-if="connection.cost > 0"
                        :key="connection.from + '_' + connection.to + '_circle'"
                        :r="6 + (connection.cost * 10) / 28"
                        :cx="(getX1(connection) + getX2(connection)) / 2"
                        :cy="(getY1(connection) + getY2(connection) - 60) / 2"
                        fill="gray"
                        stroke="black"
                    />
                    <text
                        v-if="connection.cost > 0"
                        :key="connection.from + '_' + connection.to + '_text'"
                        text-anchor="middle"
                        :style="`font-size: ${12 + (connection.cost * 6) / 28}px`"
                        fill="black"
                        :x="(getX1(connection) + getX2(connection)) / 2"
                        :y="(getY1(connection) + getY2(connection) - 60) / 2"
                    >
                        {{ connection.cost }}
                    </text>
                </template>

                <template v-for="(p, i) in G.players">
                    <PlayerBoard
                        :key="'B' + i"
                        :player="p"
                        :color="playerColors[i]"
                        :transform="`translate(1100, ${140 + 110 * i})`"
                        :owner="i"
                        :isCurrentPlayer="isCurrentPlayer(i)"
                        :ended="gameEnded(G)"
                        :isPlayer="player == i"
                        :ranking="sortedPlayers.findIndex((x) => x.id == p.id) + 1"
                        @powerPlantClick="powerPlantClick($event)"
                    />
                </template>
            </template>

            <template v-for="house in houses">
                <House
                    :key="house.id"
                    :pieceId="house.id"
                    :targetState="{ x: house.x, y: house.y }"
                    :owner="house.owner"
                    :ownerName="G.players[house.owner].name"
                    :color="house.color"
                />
            </template>

            <template v-for="coal in coals">
                <Coal
                    :key="coal.id"
                    :pieceId="coal.id"
                    :targetState="{ x: coal.x, y: coal.y }"
                    :canClick="!coal.transparent && canBuyResource('coal')"
                    :transparent="coal.transparent"
                    @click="buyResource('coal')"
                />
            </template>

            <template v-for="oil in oils">
                <Oil
                    :key="oil.id"
                    :pieceId="oil.id"
                    :targetState="{ x: oil.x, y: oil.y }"
                    :canClick="!oil.transparent && canBuyResource('oil')"
                    :transparent="oil.transparent"
                    @click="buyResource('oil')"
                />
            </template>

            <template v-for="garbage in garbages">
                <Garbage
                    :key="garbage.id"
                    :pieceId="garbage.id"
                    :targetState="{ x: garbage.x, y: garbage.y }"
                    :canClick="!garbage.transparent && canBuyResource('garbage')"
                    :transparent="garbage.transparent"
                    @click="buyResource('garbage')"
                />
            </template>

            <template v-for="uranium in uraniums">
                <Uranium
                    :key="uranium.id"
                    :pieceId="uranium.id"
                    :targetState="{ x: uranium.x, y: uranium.y }"
                    :canClick="!uranium.transparent && canBuyResource('uranium')"
                    :transparent="uranium.transparent"
                    @click="buyResource('uranium')"
                />
            </template>

            <template v-for="card in cards">
                <Card
                    :key="card.id"
                    :targetState="{ x: card.x, y: card.y }"
                    :owner="card.owner"
                    :powerPlant="card.powerPlant"
                    :canClick="canChoose() && card.isActualMarket"
                    @click="choosePowerPlant(card.powerPlant)"
                />
            </template>

            <template v-if="!preferences.disableHelp">
                <rect
                    v-if="canPass()"
                    x="1354"
                    y="14"
                    width="82"
                    height="28"
                    fill="none"
                    stroke="blue"
                    stroke-width="2px"
                    rx="2px"
                />

                <rect
                    v-if="canUndo()"
                    x="1354"
                    y="55"
                    width="82"
                    height="28"
                    fill="none"
                    stroke="blue"
                    stroke-width="2px"
                    rx="2px"
                />

                <g v-if="G && canChoose()">
                    <rect
                        v-if="G.step < 3"
                        x="950"
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
                        x="950"
                        y="5"
                        width="200"
                        height="120"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />
                </g>

                <rect
                    v-if="canBuyResource()"
                    x="15"
                    y="695"
                    width="770"
                    height="90"
                    rx="2"
                    fill="none"
                    stroke="blue"
                    stroke-width="2px"
                />

                <template v-if="G">
                    <template v-for="city in G.map.cities">
                        <circle
                            v-if="canBuild(city)"
                            :key="city.name + '_circleHelp'"
                            :class="[{ canClick: canBuild(city) }]"
                            r="18"
                            :cx="city.x"
                            :cy="city.y - 30"
                            fill="none"
                            stroke="blue"
                            stroke-width="4px"
                        />
                    </template>

                    <template v-for="(player, pi) in G.players">
                        <template v-for="(powerPlant, ppi) in player.powerPlants">
                            <rect
                                v-if="canUsePowerPlant(powerPlant)"
                                :key="pi + '_' + ppi + '_helper'"
                                :x="player.powerPlants.length < 5 ? 1120 + 80 * ppi : 1105 + 70 * ppi"
                                :y="170 + 110 * pi"
                                width="60"
                                height="40"
                                fill="none"
                                stroke="blue"
                                stroke-width="4px"
                                rx="2px"
                            />
                        </template>
                    </template>
                </template>
            </template>
        </svg>

        <div v-if="G" :class="['modal', { visible: logVisible }]">
            <div class="modal-content">
                <span class="close" @click="logVisible = false">&times;</span>
                <div class="modal-title">Log</div>
                <div class="modal-log">
                    <div v-for="(log, i) in logReversed" :key="'L' + i" class="log-line" v-html="log" />
                </div>
            </div>
        </div>

        <div v-if="G && gameEnded(G)" :class="['modal', { visible: endScoreVisible }]">
            <div class="modal-content">
                <span class="close" @click="endScoreVisible = false">&times;</span>
                <div class="modal-title">Final Score</div>
                <table class="final-score-table">
                    <tr>
                        <th><div>Player</div></th>
                        <th v-for="player in sortedPlayers" :key="'FS' + player.id">
                            <div :style="'background-color: ' + playerColors[player.id]">{{ player.name }}</div>
                        </th>
                    </tr>
                    <tr v-for="(cat, i) in ['Cities Powered', 'Money', 'Total Cities']" :key="'FC_' + cat">
                        <td>{{ cat }}</td>
                        <td v-for="player in sortedPlayers" :key="'FS' + player.id + i">
                            <div>
                                {{ i == 0 ? player.citiesPowered : i == 1 ? player.money : player.cities.length }}
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
        </div>
    </div>
</template>
<script lang="ts">
import { Vue, Component, Prop, Watch, Provide, ProvideReactive } from 'vue-property-decorator';
import { MoveName, ended, move as engineMove, playersSortedByScore } from 'powergrid-engine';
import type { GameState } from 'powergrid-engine';
import { EventEmitter } from 'events';
import { Piece, UIData, Preferences } from '../types/ui-data';
import { Card, House, Coal, Oil, Garbage, Uranium } from './pieces';
import { Button, PassButton, UndoButton, LogButton, SoundButton, HelpButton } from './buttons';
import PlayerBoard from './PlayerBoard.vue';
import Calculator from './Calculator.vue';
import { LogMove } from 'powergrid-engine/src/log';
import { City, Phase, PowerPlant, PowerPlantType, ResourceType } from 'powergrid-engine/src/gamestate';

@Component({
    components: {
        PlayerBoard,
        Card, House, Coal, Oil, Garbage, Uranium,
        PassButton,
        UndoButton,
        LogButton,
        SoundButton,
        HelpButton,
        Button,
        Calculator
    },
})
export default class Game extends Vue {
    @Prop()
    private state?: GameState;

    @Prop()
    @ProvideReactive()
    player?: number;

    @Prop()
    emitter!: EventEmitter;

    @Prop()
    @ProvideReactive()
    preferences!: Preferences;

    @Provide()
    ui: UIData = {
        waitingAnimations: 0,
    };

    @Provide()
    communicator: EventEmitter = new EventEmitter();

    @ProvideReactive()
    G?: GameState | null = null;

    // Pieces
    coals: Piece[] = [];
    oils: Piece[] = [];
    garbages: Piece[] = [];
    uraniums: Piece[] = [];
    cards: Piece[] = [];
    houses: Piece[] = [];

    playerColors = ['limegreen', 'mediumorchid', 'red', 'dodgerblue', 'yellow', 'brown'];

    animationQueue: Array<Function> = [];

    logVisible = false;
    endScoreVisible = false;

    totalBid: number = 0;

    @Watch('state', { immediate: true })
    onStateChanged(state: GameState) {
        this.replaceState(state, false);
    }

    replaceState(state: GameState, fake: boolean) {
        this.G = JSON.parse(JSON.stringify(state));

        this.createPieces();

        if (!fake && this.preferences.sound && this.G?.log[this.G?.log.length - 1].type == 'move') {
            const move = (this.G?.log[this.G?.log.length - 1] as LogMove).move;
            if (move.name == MoveName.Pass && this.G.currentPlayers.includes(this.player!)) {
                (document.getElementById('notification')!.cloneNode(true) as HTMLAudioElement).play();
            } else {
                if (move.name == MoveName.Build) {
                    setTimeout(() => {
                        (document.getElementById('piece-drop')!.cloneNode(true) as HTMLAudioElement).play();
                    }, 800);
                }
            }
        }
    }

    createPieces() {
        // Houses
        this.houses = [];
        const adjustCityCount: number[][] = [];
        for (let i = 0; i < 22; i++)
            adjustCityCount[i] = [];

        this.G?.players.forEach((player, pi) => adjustCityCount[player.cities.length].push(pi));
        this.G?.players.forEach((player, pi) => {
            player.cities
                .forEach(cityPiece => {
                    const city = this.G?.map.cities.find(city => city.name == cityPiece.name)!;
                    let offsetX, offsetY;
                    if (cityPiece.position == 0) {
                        offsetX = -6;
                        offsetY = -48;
                    } else if (cityPiece.position == 1) {
                        offsetX = -15;
                        offsetY = -34;
                    } else {
                        offsetX = 1;
                        offsetY = -34;
                    }

                    this.houses.push({
                        id: pi + '_' + cityPiece.name,
                        x: city.x + offsetX,
                        y: city.y + offsetY,
                        color: this.playerColors[pi],
                        owner: pi
                    });
                });

            let x = (adjustCityCount[player.cities.length].length == 1 ? 228 : 225) + 33 * player.cities.length;
            x += adjustCityCount[player.cities.length].indexOf(pi) % 2 * 6;

            this.houses.push({
                id: pi + '_cityCount',
                x: x,
                y: 15 + adjustCityCount[player.cities.length].indexOf(pi) * 30 / adjustCityCount[player.cities.length].length,
                color: this.playerColors[pi],
                owner: pi
            });
        });

        this.G?.playerOrder.forEach((p, i) => {
            this.houses.push({
                id: p + '_order',
                x: 20 + 30 * i,
                y: 22,
                color: this.playerColors[p],
                owner: p
            });
        });

        // Coal
        if (this.G) {
            this.coals = [];
            Array(24).fill(0)
                .forEach((_, i) => {
                    this.coals.push({
                        id: 'coal_' + i,
                        x: 668 - 23.5 * i - 14.5 * (Math.floor(i / 3)),
                        y: 708,
                        transparent: i >= this.G!.coalMarket
                    });
                });

            // Oil
            this.oils = [];
            Array(24).fill(0)
                .forEach((_, i) => {
                    this.oils.push({
                        id: 'oil_' + i,
                        x: 651 - 16 * i - 37 * (Math.floor(i / 3)),
                        y: 730,
                        transparent: i >= this.G!.oilMarket
                    });
                });

            // Garbage
            this.garbages = [];
            Array(24).fill(0)
                .forEach((_, i) => {
                    this.garbages.push({
                        id: 'garbage_' + i,
                        x: 668 - 23.5 * i - 14.5 * (Math.floor(i / 3)),
                        y: 754,
                        transparent: i >= this.G!.garbageMarket
                    });
                });

            // Uranium
            this.uraniums = [];
            Array(12).fill(0)
                .forEach((_, i) => {
                    if (i == 0) {
                        this.uraniums.push({
                            id: 'uranium_' + i,
                            x: 750,
                            y: 751,
                            transparent: i >= this.G!.uraniumMarket
                        });
                    } else if (i == 1) {
                        this.uraniums.push({
                            id: 'uranium_' + i,
                            x: 710,
                            y: 751,
                            transparent: i >= this.G!.uraniumMarket
                        });
                    } else if (i == 2) {
                        this.uraniums.push({
                            id: 'uranium_' + i,
                            x: 750,
                            y: 712,
                            transparent: i >= this.G!.uraniumMarket
                        });
                    } else if (i == 3) {
                        this.uraniums.push({
                            id: 'uranium_' + i,
                            x: 710,
                            y: 712,
                            transparent: i >= this.G!.uraniumMarket
                        });
                    } else {
                        this.uraniums.push({
                            id: 'uranium_' + i,
                            x: 1010 - 85 * i,
                            y: 732,
                            transparent: i >= this.G!.uraniumMarket
                        });
                    }
                });
        }

        // Power Plants
        this.cards = [];
        this.G?.actualMarket.forEach((card, i) => {
            if (this.G!.step < 3) {
                if (card.number != this.G?.chosenPowerPlant?.number) {
                    this.cards.push({
                        id: 'actual_' + i,
                        x: 955 + i * 65,
                        y: 24,
                        powerPlant: card,
                        isActualMarket: true
                    });
                }
            } else {
                if (card.number != this.G?.chosenPowerPlant?.number) {
                    this.cards.push({
                        id: 'actual_' + i,
                        x: 955 + (i % 3) * 65,
                        y: i < 3 ? 24 : 80,
                        powerPlant: card,
                        isActualMarket: true
                    });
                }
            }
        });

        this.G?.futureMarket.forEach((card, i) => {
            if (card.number != this.G?.chosenPowerPlant?.number) {
                this.cards.push({
                    id: 'future_' + i,
                    x: 955 + i * 65,
                    y: 90,
                    powerPlant: card,
                    isActualMarket: false
                });
            }
        });

        if (this.G?.chosenPowerPlant) {
            this.cards.push({
                id: 'chosen_',
                x: 1250,
                y: 30,
                powerPlant: this.G.chosenPowerPlant,
                isActualMarket: false
            })
        }
    }

    getX1(connection) {
        const city = this.G!.map.cities.find(city => city.name == connection.from)!;
        return city.x;
    }

    getY1(connection) {
        const city = this.G!.map.cities.find(city => city.name == connection.from)!;
        return city.y;
    }

    getX2(connection) {
        const city = this.G!.map.cities.find(city => city.name == connection.to)!;
        return city.x;
    }

    getY2(connection) {
        const city = this.G!.map.cities.find(city => city.name == connection.to)!;
        return city.y;
    }

    @Watch('ui.waitingAnimations')
    updateUI() {
        if (this.ui.waitingAnimations > 0) {
            return;
        }

        if (this.animationQueue.length > 0) {
            this.animationQueue.shift()!();
            setTimeout(() => this.updateUI());
            return;
        }
    }

    pass() {
        this.sendMove({ name: MoveName.Pass, data: true });
    }

    undo() {
        this.sendMove({ name: MoveName.Undo, data: true });
    }

    choosePowerPlant(powerPlant: PowerPlant) {
        this.sendMove({ name: MoveName.ChoosePowerPlant, data: powerPlant.number });
    }

    buyResource(resource: ResourceType) {
        this.sendMove({ name: MoveName.BuyResource, data: { resource } });
    }

    bid(bid: number) {
        this.sendMove({ name: MoveName.Bid, data: bid })
    }

    build(city: City) {
        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;
        const move = availableMoves[MoveName.Build]!.find(c => c.name == city.name)!;
        this.sendMove({ name: MoveName.Build, data: { name: city.name, price: move.price } })
    }

    powerPlantClick(powerPlant: PowerPlant) {
        if (this.G?.phase == Phase.Auction) {
            this.sendMove({ name: MoveName.DiscardPowerPlant, data: powerPlant.number });
        } else if (this.G?.phase == Phase.Bureaucracy) {
            let resourcesSpent: ResourceType[] = [];
            switch (powerPlant.type) {
                case PowerPlantType.Coal:
                    resourcesSpent = Array(powerPlant.cost).fill(ResourceType.Coal);
                    break;
                case PowerPlantType.Oil:
                    resourcesSpent = Array(powerPlant.cost).fill(ResourceType.Oil);
                    break;
                case PowerPlantType.Garbage:
                    resourcesSpent = Array(powerPlant.cost).fill(ResourceType.Garbage);
                    break;
                case PowerPlantType.Uranium:
                    resourcesSpent = Array(powerPlant.cost).fill(ResourceType.Uranium);
                    break;
                case PowerPlantType.Hybrid:
                    const currentPlayer = this.G!.players[this.player!];
                    resourcesSpent = currentPlayer.resourcesUsed;
                    resourcesSpent.sort();
                    currentPlayer.resourcesUsed = [];

                    break;
            }

            this.sendMove({ name: MoveName.UsePowerPlant, data: { powerPlant: powerPlant.number, resourcesSpent, citiesPowered: powerPlant.citiesPowered } });
        }
    }

    sendMove(move) {
        console.log(move);
        this.emitter.emit('move', move);

        this.replaceState(engineMove(this.G!, move, this.player!, true), true);
    }

    gameEnded(G: GameState) {
        return ended(G);
    }

    canMove() {
        return (
            this.player != undefined &&
            this.G &&
            this.G.currentPlayers.includes(this.player!) &&
            this.G.players[this.player!] &&
            this.G.players[this.player!].availableMoves
        );
    }

    canPass() {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        return !!availableMoves[MoveName.Pass];
    }

    canUndo() {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        return !!availableMoves[MoveName.Undo];
    }

    canBid() {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        return !!availableMoves[MoveName.Bid];
    }

    canChoose() {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        return !!availableMoves[MoveName.ChoosePowerPlant];
    }

    canBuyResource(resource?: ResourceType) {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        if (!resource) {
            return !!availableMoves[MoveName.BuyResource];
        } else {
            return !!availableMoves[MoveName.BuyResource] && availableMoves[MoveName.BuyResource]!.find(m => m.resource == resource);
        }
    }

    canBuild(city: City) {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        return !!availableMoves[MoveName.Build] && availableMoves[MoveName.Build]!.find(c => c.name == city.name);
    }

    canUsePowerPlant(powerPlant: PowerPlant) {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        if (currentPlayer.resourcesUsed.length > 0) {
            return false;
        } else if (this.G?.phase == Phase.Bureaucracy) {
            return !!availableMoves[MoveName.UsePowerPlant] && availableMoves[MoveName.UsePowerPlant]!.find(p => p.powerPlant == powerPlant.number);
        } else if (this.G?.phase == Phase.Auction) {
            return !!availableMoves[MoveName.DiscardPowerPlant] && availableMoves[MoveName.DiscardPowerPlant]!.find(p => p == powerPlant.number);
        }
    }

    toggleSound() {
        this.preferences.sound = !this.preferences.sound;
    }

    toggleHelp() {
        this.preferences.disableHelp = !this.preferences.disableHelp;
    }

    showLog() {
        this.logVisible = true;
    }

    getStatusMessage() {
        if (!this.G || this.G.currentPlayers == []) {
            return 'Game ended!';
        } else if (this.player !== undefined && this.G?.currentPlayers.includes(this.player)) {
            const currentPlayer = this.G.players[this.player];
            if (currentPlayer.availableMoves![MoveName.ChoosePowerPlant]) {
                if (currentPlayer.availableMoves![MoveName.Pass]) {
                    return 'Choose a Power Plant to start an auction, or pass.';
                }

                return 'Choose a Power Plant to start an auction.';
            } else if (currentPlayer.availableMoves![MoveName.Bid]) {
                return 'It\'s your turn to bid!';
            } else if (currentPlayer.availableMoves![MoveName.BuyResource]) {
                return 'Buy resources on the market, or pass.';
            } else if (currentPlayer.availableMoves![MoveName.Build]) {
                return 'Build a new city, or pass.';
            } else if (currentPlayer.availableMoves![MoveName.UsePowerPlant]) {
                if (currentPlayer.resourcesUsed.length != 0) {
                    return 'Choose which resources to spend.';
                }

                return 'Choose which Power Plant to use.';
            } else if (currentPlayer.availableMoves![MoveName.DiscardPowerPlant]) {
                return 'Choose which Power Plant to discard.';
            } else if (currentPlayer.availableMoves![MoveName.DiscardResources]) {
                return 'Choose which resources to discard.';
            }

            return 'It\'s your turn!';
        } else {
            let log = (this.G.log[this.G.log.length - 1] as LogMove).pretty;
            if (log) {
                while (log?.indexOf('>') != -1) {
                    log = log?.substr(0, log.indexOf('<')) + log.substr(log.indexOf('>') + 1);
                }
            }

            return log;
        }
    }

    isCurrentPlayer(player) {
        return this.G && this.G.currentPlayers.includes(player);
    }

    get logReversed() {
        let logReversed: string[] = [];
        if (this.G && this.G.log) {
            this.G.log.forEach((log) => {
                if (log.type == 'event') {
                    logReversed.push(log.event);
                } else if (log.type == 'move') {
                    logReversed.push(log.pretty);
                }
            });

            logReversed.reverse();
        }

        return logReversed;
    }

    get logReversedSimple() {
        let logReversed: string[] = [];
        if (this.G && this.G.log) {
            this.G.log.forEach((log) => {
                if (log.type == 'event') {
                    logReversed.push(log.event);
                } else if (log.type == 'move') {
                    logReversed.push(log.simple);
                }
            });

            logReversed.reverse();
        }

        return logReversed;
    }

    @Watch('G.log')
    onLogChanged() {
        this.emitter.emit('replaceLog', [...this.logReversedSimple].reverse());
    }

    get sortedPlayers() {
        return playersSortedByScore(this.G!);
    }
}
</script>
<style lang="scss">
.game {
    display: flex;
    align-items: center;
    flex-direction: column;
}

.statusBar {
    height: 40px;
    width: 100%;
    background-color: black;
    color: #fff;
    text-align: center;
    line-height: 40px;
    font-size: 20px;
    position: fixed;
}

#scene {
    margin-top: 40px;
    max-height: 100%;
    flex-grow: 1;
    margin: 40px auto auto auto;
}

body,
html {
    height: 100%;
    width: 100%;
    margin: 0;
    padding: 0;
}

text {
    font-family: 'Arial';
    pointer-events: none;
    dominant-baseline: central;

    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    user-select: none;
}

.button {
    &.enabled {
        cursor: pointer;

        &:hover {
            rect {
                fill: silver;
                stroke: white;
            }

            circle {
                fill: silver;
                stroke: white;
            }

            line {
                stroke: white;
            }

            image {
                filter: invert(1);
            }

            text {
                fill: white;
            }
        }
    }

    &:not(.enabled) {
        rect {
            stroke: silver;
        }

        circle {
            stroke: silver;
        }

        line {
            stroke: silver;
        }

        image {
            filter: invert(0.75);
        }

        text {
            fill: silver;
        }
    }
}

.modal {
    display: none; /* Hidden by default */
    position: fixed; /* Stay in place */
    z-index: 1; /* Sit on top */
    padding-top: 10vh; /* Location of the box */
    left: 0;
    top: 0;
    width: 100%; /* Full width */
    height: 100%; /* Full height */
    overflow: auto; /* Enable scroll if needed */
    background-color: rgba(0, 0, 0, 0.4); /* Black w/ opacity */

    &.visible {
        display: block;
    }
}

.modal-content {
    border-radius: 5px;
    background-color: #fefefe;
    margin: auto;
    padding: 10px 20px 20px 20px;
    border: 1px solid #888;
    position: absolute;
    left: 50%;
    transform: translate(-50%);
}

.modal-log {
    max-height: calc(80vh - 75px);
    overflow: auto;
    border: 1px solid black;
}

.log-line {
    padding: 5px;

    &:nth-last-child(even) {
        background: #ccc;
    }

    &:nth-last-child(odd) {
        background: #fff;
    }
}

.modal-title {
    font-size: 28px;
    font-weight: bold;
    text-align: center;
    margin-bottom: 10px;
}

.close {
    color: #aaaaaa;
    float: right;
    font-size: 28px;
    font-weight: bold;
}

.close:hover,
.close:focus {
    color: #000;
    text-decoration: none;
    cursor: pointer;
}

.final-score-table {
    margin: auto;
    border: 1px solid black;

    tr {
        td,
        th {
            border: 1px solid black;
            text-align: center;
            overflow: hidden;
            text-overflow: ellipsis;

            div {
                width: 120px;
                line-height: 38px;
            }
        }

        td:first-child,
        th:first-child {
            div {
                width: 250px;
            }
        }
    }
}

.confirmButton {
    margin: 5px 15px;
}
</style>
