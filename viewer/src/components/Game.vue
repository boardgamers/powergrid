<template>
    <div :class="['game', { fitToScreen: preferences.fitToScreen }]">
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
        <svg
            v-if="G"
            id="scene"
            :viewBox="G.map.viewBox ? `0 0 ${G.map.viewBox[0]} ${G.map.viewBox[1]}` : '0 0 1500 800'"
            style="width: 100%"
        >
            <rect width="100%" height="100%" x="0" y="0" fill="yellowgreen" />

            <PlayerOrder
                ref="playerOrder"
                :transform="`translate(${G.map.playerOrderPosition[0]}, ${G.map.playerOrderPosition[1]})`"
                :playerColors="playerColors"
            />

            <CityCount
                ref="cityCount"
                :transform="`translate(${G.map.cityCountPosition[0]}, ${G.map.cityCountPosition[1]})`"
                :playerColors="playerColors"
                :citiesToEndGame="G.citiesToEndGame"
                :citiesToStep2="G.citiesToStep2"
            />

            <PowerPlantMarket
                ref="powerPlantMarket"
                :transform="`translate(${G.map.powerPlantMarketPosition[0]}, ${G.map.powerPlantMarketPosition[1]})`"
                :canBid="canBid()"
                :canChoose="canChoose()"
                :chooseablePowerPlants="getChooseablePowerPlants()"
                :cardsLeft="G.cardsLeft"
                :minBid="G.currentBid + 1 || G.minimunBid"
                :maxBid="G.players[player] ? G.players[player].money : 0"
                :nextCardWeak="G.nextCardWeak"
                :plantDiscountActive="G.plantDiscountActive"
                @choosePowerPlant="choosePowerPlant($event)"
                @bid="bid($event)"
            />

            <Map
                ref="map"
                :transform="`translate(${G.map.mapPosition[0]}, ${G.map.mapPosition[1]})`"
                :playerColors="playerColors"
                :cities="G.map.cities"
                :connections="G.map.connections"
                :polygons="G.map.polygons"
                :buildableCities="getBuildableCities()"
                @build="build($event)"
            />

            <Resources
                ref="resources"
                :transform="`translate(${G.map.supplyPosition[0]}, ${G.map.supplyPosition[1]})`"
                :isUsaRecharged="G.options.variant == 'recharged' && G.map.name == 'USA'"
                :isMiddleEast="G.map.name == 'Middle East'"
                :isIndiaResourceMarket="G.map.name == 'India' && G.coalPrices && G.garbagePrices && G.uraniumPrices"
                :availableSurplusOil="
                    G.map.name == 'Middle East' ? Math.max(G.oilMarket - G.oilPrices.filter((p) => p > 1).length, 0) : 0
                "
                :buyableResources="buyableResources()"
                :resourceResupply="getResourceResupply()"
                @buyResource="buyResource($event)"
            />

            <g :transform="`translate(${G.map.roundInfoPosition[0]}, ${G.map.roundInfoPosition[1]})`">
                <template v-if="gameEnded(G)">
                    <Button
                        :transform="`translate(20, 50)`"
                        :width="130"
                        :text="'Final Score'"
                        @click="endScoreVisible = true"
                    />
                    <template v-if="G.options.trackTotalSpent">
                        <Button
                            :transform="`translate(180, 50)`"
                            :width="120"
                            :text="'Game Stats'"
                            @click="spendingVisible = true"
                        />
                    </template>
                </template>
                <template v-else>
                    <text x="10" y="20" font-weight="600" fill="black" style="font-size: 32px">
                        Round: {{ G.round }}
                    </text>
                    <text x="10" y="60" font-weight="600" fill="black" style="font-size: 32px">Step: {{ G.step }}</text>
                    <text x="10" y="100" font-weight="600" fill="black" style="font-size: 32px">
                        Phase: {{ G.phase }}
                    </text>
                </template>
            </g>

            <g :transform="`translate(${G.map.buttonsPosition[0]}, ${G.map.buttonsPosition[1]})`">
                <PassButton
                    transform="translate(15, 15)"
                    :enabled="canPass()"
                    :highlightButton="canPass() && !preferences.disableHelp"
                    :text="canUndo() ? 'Done' : 'Pass'"
                    @click="checkPass()"
                />
                <UndoButton
                    transform="translate(15, 56)"
                    :enabled="canUndo()"
                    :highlightButton="canUndo() && !preferences.disableHelp"
                    @click="undo()"
                />
                <LogButton transform="translate(15, 97)" @click="showLog()" />
                <SoundButton transform="translate(110, 13)" :isOn="preferences.sound" @click="toggleSound()" />
                <HelpButton transform="translate(110, 54)" :isOn="!preferences.disableHelp" @click="toggleHelp()" />
                <RulesButton transform="translate(110, 95)" @click="rulesVisible = true" />
            </g>

            <template v-for="(playerIndex, i) in adjustedPlayerOrder">
                <PlayerBoard
                    :key="'B' + playerIndex"
                    :transform="`translate(${G.map.playerBoardsPosition[0]}, ${
                        G.map.playerBoardsPosition[1] + 110 * i
                    })`"
                    :player="G.players[playerIndex]"
                    :color="playerColors[playerIndex]"
                    :avatar="avatars[playerIndex]"
                    :owner="playerIndex"
                    :isCurrentPlayer="isCurrentPlayer(playerIndex)"
                    :ended="gameEnded(G)"
                    :isPlayer="player == playerIndex"
                    :ranking="sortedPlayers.findIndex((x) => x.id == G.players[playerIndex].id) + 1"
                    :showMoney="player == playerIndex || gameEnded(G) || G.options.showMoney"
                    :showBid="!G.options.fastBid"
                    :phase="G.phase"
                    @powerPlantClick="powerPlantClick($event)"
                    @discardResource="discardResource($event)"
                />
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

        <div v-if="G" :class="['modal', { visible: confirmVisible }]">
            <div class="modal-content">
                <span class="close" @click="confirmVisible = false">&times;</span>
                <div class="modal-title">Confirm</div>
                <div class="confirm-message">{{ confirmMessage }}</div>
                <div class="confirm-buttons">
                    <button class="confirm-button" @click="confirmPass()">OK</button>
                    <button class="confirm-button" @click="confirmVisible = false">Cancel</button>
                </div>
            </div>
        </div>

        <div v-if="G && discardedPowerPlant" :class="['modal', { visible: discardVisible }]">
            <div class="modal-content">
                <div class="modal-title">Discard Resources</div>
                <div class="confirm-message">Choose which resources to discard:</div>
                <div
                    v-for="(r, i) in resourcesToDiscard"
                    :key="'R' + i"
                    class="confirm-message"
                    style="text-align: center"
                >
                    {{ r.name }}: <input v-model="r.value" type="number" min="0" :max="r.max" style="width: 3em" />
                </div>
                <div class="confirm-buttons">
                    <button class="confirm-button" :disabled="discardInvalid()" @click="confirmDiscard()">OK</button>
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

        <div v-if="G && gameEnded(G)" :class="['modal', { visible: spendingVisible }]">
            <div class="modal-content">
                <span class="close" @click="spendingVisible = false">&times;</span>
                <div class="modal-title">Spending</div>
                <table class="spending-table">
                    <tr>
                        <th><div>Player</div></th>
                        <th v-for="player in sortedPlayers" :key="'FS' + player.id">
                            <div :style="'background-color: ' + playerColors[player.id]">{{ player.name }}</div>
                        </th>
                    </tr>
                    <tr
                        v-for="(cat, i) in [
                            'Income',
                            'Spending: Cities',
                            'Spending: Connections',
                            'Spending: Plants',
                            'Spending: Resources',
                        ]"
                        :key="'FC_' + cat"
                    >
                        <td>{{ cat }}</td>
                        <td v-for="player in sortedPlayers" :key="'FS' + player.id + i">
                            <div>
                                {{
                                    i == 0
                                        ? player.totalIncome
                                        : i == 1
                                        ? player.totalSpentCities
                                        : i == 2
                                        ? player.totalSpentConnections
                                        : i == 3
                                        ? player.totalSpentPlants
                                        : player.totalSpentResources
                                }}
                            </div>
                        </td>
                    </tr>
                </table>
            </div>
        </div>

        <div v-if="G" :class="['modal', { visible: rulesVisible }]">
            <div class="modal-content">
                <span class="close" @click="rulesVisible = false">&times;</span>
                <div class="modal-title">Rules Summary</div>
                <div class="modal-body">
                    <div>
                        <strong>Phases:</strong>
                        <ul>
                            <li>
                                <strong>Determine Turn Order</strong> by number of cities built and highest power plant
                                owned
                            </li>
                            <li>
                                <strong>Buy Power Plants</strong> from the actual market (minimun bid is power plant
                                number)
                            </li>
                            <li>
                                <strong>Buy Resources</strong> in <strong>reverse</strong> turn order from the resource
                                market
                            </li>
                            <li>
                                <strong>Build Cities</strong> in <strong>reverse</strong> turn order paying
                                <strong>10/15/20</strong> plus connection cost
                            </li>
                            <li>
                                <strong>Bureaucracy:</strong> spend resources to use power plants, collect money
                                according to cities supplied, resupply resource market
                            </li>
                        </ul>
                    </div>
                    <div>
                        <strong>Steps:</strong>
                        <ul>
                            <li>
                                <strong>Step 1:</strong>
                                <ul>
                                    <li><strong>One</strong> player per city</li>
                                    <li>
                                        Resource Resupply: <strong>{{ G.resourceResupply[0] }}</strong>
                                    </li>
                                    <li>Bureaucracy: remove <strong>highest</strong> power plant from market</li>
                                </ul>
                            </li>
                            <li>
                                <strong>Step 2:</strong>
                                <ul>
                                    <li>
                                        Starts after building phase where a player has
                                        <strong>{{ G.citiesToStep2 }}</strong> or more cities
                                    </li>
                                    <li><strong>Two</strong> players per city</li>
                                    <li>
                                        Resource Resupply: <strong>{{ G.resourceResupply[1] }}</strong>
                                    </li>
                                    <li>Bureaucracy: remove <strong>highest</strong> power plant from market</li>
                                </ul>
                            </li>
                            <li>
                                <strong>Step 3:</strong>
                                <ul>
                                    <li>Starts after the "Step 3" card is drawn from the deck</li>
                                    <li><strong>Three</strong> players per city</li>
                                    <li>
                                        Resource Resupply: <strong>{{ G.resourceResupply[2] }}</strong>
                                    </li>
                                    <li>Bureaucracy: remove <strong>lowest</strong> power plant from market</li>
                                    <li>All power plants available for auction</li>
                                </ul>
                            </li>
                        </ul>
                    </div>
                    <div>
                        Game ends after building phase where a player has <strong>{{ G.citiesToEndGame }}</strong> or
                        more cities.<br />
                        The winner is the player that can power the most cities. Money and number of cities built are
                        tiebreakers.
                    </div>
                    <template v-if="G.map.mapSpecificRules">
                        <br />
                        <div>
                            <strong>Map Specific Rules:</strong><br />
                            <span style="white-space: pre">{{ G.map.mapSpecificRules }}</span>
                        </div>
                    </template>
                    <br />
                    <div>
                        <strong>Payment Table</strong>
                        <table class="payment-table">
                            <tr>
                                <td><strong>Cities</strong></td>
                                <template v-for="index in G.citiesToEndGame">
                                    <td :key="'cities' + index">{{ index - 1 }}</td>
                                </template>
                            </tr>
                            <tr>
                                <td><strong>Payment</strong></td>
                                <template v-for="index in G.citiesToEndGame">
                                    <td :key="'payment' + index">${{ G.paymentTable[index - 1] }}</td>
                                </template>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
<script lang="ts">
import { Vue, Component, Prop, Watch, Provide, ProvideReactive, Ref } from 'vue-property-decorator';
import { MoveName, ended, playersSortedByScore, reconstructState } from 'powergrid-engine';
import type { GameState } from 'powergrid-engine';
import { EventEmitter } from 'events';
import { UIData, Preferences } from '../types/ui-data';
import { Card, House, Coal, Oil, Garbage, Uranium } from './pieces';
import { Button, PassButton, UndoButton, LogButton, SoundButton, HelpButton, RulesButton } from './buttons';
import PlayerBoard from './PlayerBoard.vue';
import Calculator from './Calculator.vue';
import PowerPlantMarket from './boards/PowerPlantMarket.vue';
import PlayerOrder from './boards/PlayerOrder.vue';
import CityCount from './boards/CityCount.vue';
import Map from './boards/Map.vue';
import Resources from './boards/Resources.vue';
import { LogMove } from 'powergrid-engine/src/log';
import { Phase, PowerPlant, PowerPlantType, ResourceType } from 'powergrid-engine/src/gamestate';
import { City } from 'powergrid-engine/src/maps';

@Component({
    created(this: Game) {
        this.emitter.on('replayStart', () => {
            this.paused = true;
            this.emitter.emit('replay:info', {
                start: 1,
                current: this.G!.log.filter(l => l.type == 'move').length,
                end: this._futureState!.log.filter(l => l.type == 'move').length,
            });
        });

        this.emitter.on('replayTo', (to: number) => {
            const log = this._futureState!.log.map((l, i) => ({ index: i, ...l })).filter(l => l.type == 'move');
            to = log[to - 1].index;

            this.replaceState(reconstructState(this._futureState!, to + 1), false);

            this.emitter.emit('replay:info', {
                start: 1,
                current: this.G!.log.filter(l => l.type == 'move').length + this.G!.hiddenLog.length,
                end: this._futureState!.log.filter(l => l.type == 'move').length,
            });
        });

        this.emitter.on('replayEnd', () => {
            this.paused = false;
            this.emitter.emit('fetchState');
        });
    },
    components: {
        PlayerBoard,
        Card,
        House,
        Coal,
        Oil,
        Garbage,
        Uranium,
        PassButton,
        UndoButton,
        LogButton,
        SoundButton,
        HelpButton,
        RulesButton,
        Button,
        Calculator,
        PowerPlantMarket,
        PlayerOrder,
        CityCount,
        Map,
        Resources
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
    avatars!: string[];

    @Prop()
    @ProvideReactive()
    preferences!: Preferences;

    @Provide()
    ui: UIData = {
        waitingAnimations: 0,
    };

    paused = false;

    @Provide()
    communicator: EventEmitter = new EventEmitter();

    @ProvideReactive()
    G?: GameState | null = null;
    _futureState?: GameState;

    playerColors = ['limegreen', 'mediumorchid', 'red', 'dodgerblue', 'yellow', 'brown'];

    animationQueue: Array<Function> = [];

    logVisible = false;
    endScoreVisible = false;
    spendingVisible = false;
    rulesVisible = false;

    totalBid: number = 0;

    confirmMessage = '';
    confirmVisible = false;

    discardedPowerPlant: PowerPlant | null = null;
    discardVisible: boolean = false;
    resourcesToDiscard: { name: string, max: number, value: string }[] = [];

    disablePass: boolean = false;

    @Ref() powerPlantMarket!: PowerPlantMarket;
    @Ref() playerOrder!: PlayerOrder;
    @Ref() cityCount!: CityCount;
    @Ref() map!: Map;
    @Ref() resources!: Resources;

    @Watch('state', { immediate: true })
    onStateChanged(state: GameState) {
        this.replaceState(state);
    }

    replaceState(state: GameState, replaceState = true) {
        if (replaceState) {
            this._futureState = state;
        }

        // if player is selecting resources, keep the state
        let player: any;
        if (this.player != null) {
            if (this.G && this.G.players && this.G.players[this.player].resourcesUsed.some((r) => r == null)) {
                player = {
                    coalLeft: this.G.players[this.player].coalLeft,
                    oilLeft: this.G.players[this.player].oilLeft,
                    resourcesUsed: this.G.players[this.player].resourcesUsed
                };
            }
        }

        this.G = JSON.parse(JSON.stringify(state));

        if (player) {
            Object.assign(this.G!.players![this.player!], player);
        }

        if (this.G) {
            // workaround: refs are not set the first time
            this.$nextTick(() => {
                this.powerPlantMarket.createPieces(this.G!);
                this.playerOrder.createPieces(this.G!);
                this.cityCount.createPieces(this.G!);
                this.map.createPieces(this.G!);
                this.resources.createPieces(this.G!);
            });
        }

        if (this.preferences.sound && this.G?.log[this.G?.log.length - 1].type == 'move') {
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

    checkPass() {
        if (this.G && this.player != null && !this.G.chosenPowerPlant) {
            const player = this.G.players[this.player];
            if (player && player.availableMoves && Object.keys(player.availableMoves).length > 1) {
                if (this.G.phase == Phase.Bureaucracy && player.powerPlantsNotUsed.length > 0
                        && Object.keys(player.availableMoves).includes('UsePowerPlant')) {
                    this.confirmMessage = 'Are you sure you want to pass? You have unused power plants!';
                    this.confirmVisible = true;
                    return;
                } else if (
                    this.G.phase != Phase.Bureaucracy ||
                    player.powerPlantsNotUsed.length == player.powerPlants.length
                ) {
                    const lastMove = this.G.log[this.G.log.length - 1] as LogMove;
                    if (lastMove.player != this.player || lastMove.move.name == MoveName.Pass) {
                        switch (this.G.phase) {
                            case Phase.Auction:
                                this.confirmMessage = 'Are you sure you want to skip auctions?';
                                break;
                            case Phase.Resources:
                                this.confirmMessage = 'Are you sure you want to skip buying resources?';
                                break;
                            case Phase.Building:
                                this.confirmMessage = 'Are you sure you want to skip building?';
                                break;
                            case Phase.Bureaucracy:
                                this.confirmMessage = 'Are you sure you want to pass? You didn\'t use any power plant!';
                                break;
                            default:
                                this.confirmMessage = 'Are you sure you want to pass?';
                        }

                        this.confirmVisible = true;
                        return;
                    }
                }
            }
        }

        this.pass();
    }

    confirmPass() {
        this.confirmVisible = false;
        this.pass();
    }

    pass() {
        this.sendMove({ name: MoveName.Pass, data: true });
    }

    undo() {
        this.sendMove({ name: MoveName.Undo, data: this.preferences.undoWholeTurn });
    }

    choosePowerPlant(powerPlant: PowerPlant) {
        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        if (availableMoves.ChoosePowerPlant && availableMoves.ChoosePowerPlant.includes(powerPlant.number)) {
            this.sendMove({ name: MoveName.ChoosePowerPlant, data: powerPlant.number });
        }
    }

    buyResource(resource: ResourceType) {
        this.sendMove({ name: MoveName.BuyResource, data: { resource } });
    }

    bid(bid: number) {
        this.sendMove({ name: MoveName.Bid, data: bid });
    }

    build(city: City) {
        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;
        const move = availableMoves[MoveName.Build]!.find((c) => c.name == city.name)!;
        this.sendMove({ name: MoveName.Build, data: { name: city.name, price: move.price } });
    }

    confirmDiscard() {
        const values = this.resourcesToDiscard.map(r => parseInt(r.value));
        if (values.reduce((acc, cur) => acc + cur, 0) > 0) {
            this.sendMove({ name: MoveName.DiscardPowerPlant, data: this.discardedPowerPlant!.number, extra: values });
        } else {
            this.sendMove({ name: MoveName.DiscardPowerPlant, data: this.discardedPowerPlant!.number });
        }

        this.discardedPowerPlant = null;
        this.discardVisible = false;
    }

    discardInvalid() {
        const currentPlayer = this.G!.players[this.player!];
        let hybridCapacityUsed;
        switch (this.discardedPowerPlant!.type) {
            case PowerPlantType.Coal:
                hybridCapacityUsed = currentPlayer.hybridCapacity - this.discardedPowerPlant!.cost * 2 > 0 ? Math.max(0, currentPlayer.oilLeft - currentPlayer.oilCapacity) : 0;
                return currentPlayer.coalCapacity + currentPlayer.hybridCapacity - this.discardedPowerPlant!.cost * 2 + parseInt(this.resourcesToDiscard[0].value) < currentPlayer.coalLeft + hybridCapacityUsed;

            case PowerPlantType.Oil:
                hybridCapacityUsed = currentPlayer.hybridCapacity - this.discardedPowerPlant!.cost * 2 > 0 ? Math.max(0, currentPlayer.coalLeft - currentPlayer.coalCapacity) : 0;
                return currentPlayer.oilCapacity + currentPlayer.hybridCapacity - this.discardedPowerPlant!.cost * 2 + parseInt(this.resourcesToDiscard[0].value) < currentPlayer.oilLeft + hybridCapacityUsed;

            case PowerPlantType.Garbage:
                return currentPlayer.garbageCapacity - this.discardedPowerPlant!.cost * 2 - currentPlayer.garbageLeft + parseInt(this.resourcesToDiscard[0].value) < 0;

            case PowerPlantType.Uranium:
                return currentPlayer.uraniumCapacity - this.discardedPowerPlant!.cost * 2 - currentPlayer.uraniumLeft + parseInt(this.resourcesToDiscard[0].value) < 0;

            case PowerPlantType.Hybrid:
                hybridCapacityUsed = currentPlayer.hybridCapacity - this.discardedPowerPlant!.cost * 2 > 0 ? Math.max(0, currentPlayer.oilLeft - currentPlayer.oilCapacity) : 0;
                if (currentPlayer.coalCapacity + currentPlayer.hybridCapacity - this.discardedPowerPlant!.cost * 2 + parseInt(this.resourcesToDiscard[0].value) < currentPlayer.coalLeft + hybridCapacityUsed) {
                    return true;
                }

                hybridCapacityUsed = currentPlayer.hybridCapacity - this.discardedPowerPlant!.cost * 2 > 0 ? Math.max(0, currentPlayer.coalLeft - currentPlayer.coalCapacity) : 0;
                if (currentPlayer.oilCapacity + currentPlayer.hybridCapacity - this.discardedPowerPlant!.cost * 2 + parseInt(this.resourcesToDiscard[1].value) < currentPlayer.oilLeft + hybridCapacityUsed) {
                    return true;
                }

                return false;
        }

        return true;
    }

    powerPlantClick(powerPlant: PowerPlant) {
        if (this.G?.phase == Phase.Auction) {
            if (powerPlant.type == PowerPlantType.Wind || powerPlant.type == PowerPlantType.Nuclear) {
                this.sendMove({ name: MoveName.DiscardPowerPlant, data: powerPlant.number });
            } else {
                const currentPlayer = this.G!.players[this.player!];

                switch (powerPlant.type) {
                    case PowerPlantType.Coal:
                        if (currentPlayer.powerPlants.filter(pp => pp.type == powerPlant.type).length + currentPlayer.powerPlants.filter(pp => pp.type == PowerPlantType.Hybrid).length == 1) {
                            this.sendMove({ name: MoveName.DiscardPowerPlant, data: powerPlant.number });
                            return;
                        }

                        if (currentPlayer.coalLeft == 0) {
                            this.sendMove({ name: MoveName.DiscardPowerPlant, data: powerPlant.number });
                            return;
                        }

                        this.resourcesToDiscard = [{ name: 'Coal', value: '0', max: currentPlayer.coalLeft }];
                        break;

                    case PowerPlantType.Oil:
                        if (currentPlayer.powerPlants.filter(pp => pp.type == powerPlant.type).length + currentPlayer.powerPlants.filter(pp => pp.type == PowerPlantType.Hybrid).length == 1) {
                            this.sendMove({ name: MoveName.DiscardPowerPlant, data: powerPlant.number });
                            return;
                        }

                        if (currentPlayer.oilLeft == 0) {
                            this.sendMove({ name: MoveName.DiscardPowerPlant, data: powerPlant.number });
                            return;
                        }

                        this.resourcesToDiscard = [{ name: 'Oil', value: '0', max: currentPlayer.oilLeft }];
                        break;

                    case PowerPlantType.Garbage:
                        if (currentPlayer.powerPlants.filter(pp => pp.type == powerPlant.type).length == 1) {
                            this.sendMove({ name: MoveName.DiscardPowerPlant, data: powerPlant.number });
                            return;
                        }

                        if (currentPlayer.garbageLeft == 0) {
                            this.sendMove({ name: MoveName.DiscardPowerPlant, data: powerPlant.number });
                            return;
                        }

                        this.resourcesToDiscard = [{ name: 'Garbage', value: '0', max: currentPlayer.garbageLeft }];

                        break;

                    case PowerPlantType.Uranium:
                        if (currentPlayer.powerPlants.filter(pp => pp.type == powerPlant.type).length == 1) {
                            this.sendMove({ name: MoveName.DiscardPowerPlant, data: powerPlant.number });
                            return;
                        }

                        if (currentPlayer.uraniumLeft == 0) {
                            this.sendMove({ name: MoveName.DiscardPowerPlant, data: powerPlant.number });
                            return;
                        }

                        this.resourcesToDiscard = [{ name: 'Uranium', value: '0', max: currentPlayer.uraniumLeft }];
                        break;

                    case PowerPlantType.Hybrid:
                        if (currentPlayer.powerPlants.filter(pp => pp.type == powerPlant.type).length + currentPlayer.powerPlants.filter(pp => pp.type == PowerPlantType.Coal).length + currentPlayer.powerPlants.filter(pp => pp.type == PowerPlantType.Oil).length == 1) {
                            this.sendMove({ name: MoveName.DiscardPowerPlant, data: powerPlant.number });
                            return;
                        }

                        if (currentPlayer.coalLeft + currentPlayer.oilLeft == 0) {
                            this.sendMove({ name: MoveName.DiscardPowerPlant, data: powerPlant.number });
                            return;
                        }

                        this.resourcesToDiscard = [{ name: 'Coal', value: '0', max: currentPlayer.coalLeft }, { name: 'Oil', value: '0', max: currentPlayer.oilLeft }];
                        break;
                }

                this.discardedPowerPlant = powerPlant;
                this.discardVisible = true;
            }
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
                    currentPlayer.powerPlantsNotUsed = currentPlayer.powerPlantsNotUsed.filter((x) => x != powerPlant.number);

                    break;
            }

            this.sendMove({
                name: MoveName.UsePowerPlant,
                data: { powerPlant: powerPlant.number, resourcesSpent, citiesPowered: powerPlant.citiesPowered },
            });

            this.disablePass = true;
            setTimeout(() => this.disablePass = false, 1000);
        }
    }

    discardResource(resource) {
        this.sendMove({
            name: MoveName.DiscardResources,
            data: resource,
        });
    }

    sendMove(move) {
        if (!this.paused) {
            this.emitter.emit('move', move);
        }
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

        if (this.disablePass) return false;

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

    buyableResources() {
        if (!this.canMove()) return [];

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        return !!availableMoves[MoveName.BuyResource] && availableMoves[MoveName.BuyResource]!.map((m) => m.resource) || [];
    }

    canBuyResource(resource?: ResourceType) {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        if (!resource) {
            return !!availableMoves[MoveName.BuyResource];
        } else {
            return (
                !!availableMoves[MoveName.BuyResource] &&
                availableMoves[MoveName.BuyResource]!.find((m) => m.resource == resource)
            );
        }
    }

    getChooseablePowerPlants() {
        if (!this.canMove()) return [];

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        return availableMoves[MoveName.ChoosePowerPlant];
    }

    getBuildableCities() {
        if (!this.canMove()) return [];

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        return availableMoves[MoveName.Build] && availableMoves[MoveName.Build]!.map((c) => c.name) || [];
    }

    canBuild(city: City) {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        return !!availableMoves[MoveName.Build] && availableMoves[MoveName.Build]!.find((c) => c.name == city.name);
    }

    canUsePowerPlant(powerPlant: PowerPlant) {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        if (currentPlayer.resourcesUsed.length > 0) {
            return false;
        } else if (this.G?.phase == Phase.Bureaucracy) {
            return (
                !!availableMoves[MoveName.UsePowerPlant] &&
                availableMoves[MoveName.UsePowerPlant]!.find((p) => p.powerPlant == powerPlant.number)
            );
        } else if (this.G?.phase == Phase.Auction) {
            return (
                !!availableMoves[MoveName.DiscardPowerPlant] &&
                availableMoves[MoveName.DiscardPowerPlant]!.find((p) => p == powerPlant.number)
            );
        }
    }

    toggleSound() {
        const newSound = !this.preferences.sound;

        this.emitter.emit('update:preference', { name: 'sound', value: newSound });
        this.preferences.sound = newSound;
    }

    toggleHelp() {
        const newVal = !this.preferences.disableHelp;

        this.emitter.emit('update:preference', { name: 'disableHelp', value: newVal });
        this.preferences.disableHelp = newVal;
    }

    showLog() {
        this.logVisible = true;
    }

    getStatusMessage() {
        if (!this.G || this.G.log.length == 1) {
            return 'Game Start!';
        } else if (this.G.currentPlayers == []) {
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
            let log = this.G.log[this.G.log.length - 1];
            if (log.type == 'move') {
                return log.simple;
            } else if (log.type == 'event') {
                return log.event;
            }
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
                    logReversed.push(log.pretty || log.event);
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

    get adjustedPlayerOrder() {
        if (!this.G) {
            return [];
        }

        if (!this.preferences.adjustPlayerOrder) {
            return this.G.players.map((_p, i) => i); // 0 1 2 3 ...
        }

        if (this.G.phase == Phase.Auction) {
            return this.G.playerOrder;
        }

        return this.G.playerOrder.reverse();
    }

    getResourceResupply() {
        if (this.G) {
            let str = this.G.resourceResupply[this.G.step - 1];
            str = str.substr(1, str.length - 2);
            return str.split(',');
        }

        return [0, 0, 0, 0];
    }
}
</script>
<style lang="scss">
ul {
    margin-block-start: 0;
}

.game {
    display: flex;
    align-items: center;
    flex-direction: column;
}

.fitToScreen {
    height: 100%;
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
    max-height: calc(100% - 40px);
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
    &.highlightButton {
        rect {
            stroke: blue;
            stroke-width: 4px;
        }
    }

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
}

@media only screen and (min-width: 1240px) {
    .modal-content {
        position: absolute;
        left: 50%;
        transform: translate(-50%);
    }
}

.modal-body {
    max-height: calc(80vh - 64px);
    overflow: auto;
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

.payment-table {
    border: 1px solid black;
    margin: 5px auto;

    tr {
        td {
            border: 1px solid black;
            text-align: center;
            padding: 0 10px 0 10px;
        }
    }
}

.final-score-table,
.spending-table {
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

.confirm-message {
    font-size: 18px;
    padding: 10px;
}

.confirm-buttons {
    text-align: center;
}

.confirm-button {
    margin: 15px 0 0 15px;
}
</style>
