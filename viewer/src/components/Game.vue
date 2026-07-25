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
                :citiesToStep2="G.map.name === 'Manhattan' ? undefined : G.citiesToStep2"
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
                :transform="mapTransform"
                :playerColors="playerColors"
                :cities="G.map.cities"
                :connections="G.map.connections"
                :polygons="G.map.polygons"
                :buildableCities="getBuildableCities()"
                :blockedCities="G.blockedCities"
                :pickableRegions="getPickableRegions()"
                :noUraniumRegions="G.map.noUraniumRegions"
                :devBackdrop="G.map.devBackdrop"
                :mapRotation="G.map.mapRotation || 0"
                @build="build($event)"
                @pickRegion="pickRegion($event)"
            />

            <!-- Japan: Free Jump indicator -->
            <g v-if="G.map.name === 'Japan'">
                <text x="330" y="93" font-size="20" font-weight="bold" fill="black">Free Jump:</text>
                <template v-for="(fjPlayer, i) in G.players">
                    <g
                        :key="'fj_' + i"
                        :transform="`translate(${480 + i * 30}, 80) scale(0.045)`"
                        :opacity="playerHasUsedFreeJump(i) ? 0.2 : 1"
                    >
                        <path
                            d="M187.698 263.636V456.017L3 341.204V169.522L80.8579 108.141L187.698 263.636Z"
                            :fill="playerColors[i]"
                            stroke="#010101"
                            stroke-width="12"
                            stroke-miterlimit="10"
                        />
                        <path
                            d="M395.724 136.361V300.164L187.698 456.017V263.636L395.724 136.361Z"
                            :fill="playerColors[i]"
                            stroke="#010101"
                            stroke-width="12"
                            stroke-miterlimit="10"
                        />
                        <path
                            d="M395.724 136.361L187.698 263.636L80.8579 108.141L304.771 4L395.724 136.361Z"
                            :fill="playerColors[i]"
                            stroke="#010101"
                            stroke-width="12"
                            stroke-miterlimit="10"
                        />
                    </g>
                </template>
            </g>

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
                :coalStorage="G.coalStorage"
                :resourceResupply="getResourceResupply()"
                :resourceResupplyNorth="getResourceResupplyNorth()"
                @buyResource="buyResource($event)"
            />

            <!-- Australia: uranium-mine selling table. Six price rows $7 (top) →
                 $2 (bottom), two token slots each. Sellers place one token per mine
                 on the highest empty slot; the resource refill removes from the
                 cheap (bottom) end. Lives in the clear upper-left margin. -->
            <g v-if="G.map.name === 'Australia' && G.uraniumMineMarket" transform="translate(15, 70)">
                <rect x="0" y="0" width="104" height="430" rx="6" fill="#8aa84a" stroke="#4d6322" stroke-width="3" />
                <text x="52" y="22" text-anchor="middle" font-weight="700" fill="black" style="font-size: 15px">
                    Uranium
                </text>
                <text x="52" y="38" text-anchor="middle" font-weight="600" fill="black" style="font-size: 11px">
                    mine market
                </text>
                <g v-for="row in 6" :key="'uraniumRow' + row" :transform="`translate(0, ${50 + (row - 1) * 59})`">
                    <text x="16" y="32" text-anchor="middle" font-weight="700" fill="black" style="font-size: 15px">
                        ${{ 8 - row }}
                    </text>
                    <rect
                        x="36"
                        y="14"
                        width="26"
                        height="26"
                        rx="3"
                        fill="goldenrod"
                        stroke="#4d6322"
                        stroke-width="1.5"
                    />
                    <rect
                        x="68"
                        y="14"
                        width="26"
                        height="26"
                        rx="3"
                        fill="goldenrod"
                        stroke="#4d6322"
                        stroke-width="1.5"
                    />
                    <circle
                        v-if="(G.uraniumMineMarket[6 - row] || 0) >= 1"
                        cx="49"
                        cy="27"
                        r="10"
                        fill="#46c655"
                        stroke="#1f5c25"
                        stroke-width="2"
                    />
                    <circle
                        v-if="(G.uraniumMineMarket[6 - row] || 0) >= 2"
                        cx="81"
                        cy="27"
                        r="10"
                        fill="#46c655"
                        stroke="#1f5c25"
                        stroke-width="2"
                    />
                </g>
                <!-- Removal rate: tokens taken from the cheapest slots each refill (current step). -->
                <line x1="10" y1="402" x2="94" y2="402" stroke="#4d6322" stroke-width="1" />
                <text x="52" y="420" text-anchor="middle" font-weight="700" fill="#22340f" style="font-size: 12px">
                    refill −{{ G.map.uraniumMineResupply[G.players.length - 2][G.step - 1] }}/rnd
                </text>
            </g>

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
                    :isAustralia="G.map.name === 'Australia'"
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

        <div v-if="G && freeJumpCity" :class="['modal', { visible: freeJumpVisible }]">
            <div class="modal-content">
                <span
                    class="close"
                    @click="
                        freeJumpVisible = false;
                        freeJumpCity = null;
                    "
                    >&times;</span
                >
                <div class="modal-title">Free Jump — {{ freeJumpCity.name }}</div>
                <div class="confirm-message" v-if="freeJumpNormalPrice !== null">
                    Use your <b>Free Jump</b> to build here for ${{ freeJumpSlotPrice }} (slot cost only), or pay the
                    full connection price of ${{ freeJumpNormalPrice }} and save the jump for later.
                </div>
                <div class="confirm-message" v-else>
                    Use your <b>Free Jump</b> to build here for ${{ freeJumpSlotPrice }} (slot cost only)? This city is
                    not reachable from your network otherwise.
                </div>
                <div class="confirm-buttons">
                    <button class="confirm-button" @click="confirmFreeJump(true)">
                        Use Free Jump (${{ freeJumpSlotPrice }})
                    </button>
                    <button v-if="freeJumpNormalPrice !== null" class="confirm-button" @click="confirmFreeJump(false)">
                        Pay Full Price (${{ freeJumpNormalPrice }})
                    </button>
                    <button
                        class="confirm-button"
                        @click="
                            freeJumpVisible = false;
                            freeJumpCity = null;
                        "
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>

        <!-- chooseColors: shown on the current player's turn during the color draft.
             No close button — picking a color is required to proceed. -->
        <div v-if="G && canChooseColor()" class="modal visible">
            <div class="modal-content">
                <div class="modal-title">Choose your color</div>
                <div class="confirm-message">Pick the color you'll play as.</div>
                <div class="confirm-buttons">
                    <button
                        v-for="color in getChooseableColors()"
                        :key="color"
                        class="confirm-button"
                        :style="`background-color: ${color}; color: white; text-shadow: 0 0 3px black;`"
                        @click="chooseColor(color)"
                    >
                        {{ color }}
                    </button>
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
                    <tr v-for="row in spendingRows" :key="'FC_' + row.label">
                        <td>{{ row.label }}</td>
                        <td v-for="player in sortedPlayers" :key="'FS' + player.id + row.label">
                            <div>{{ row.value(player) }}</div>
                        </td>
                    </tr>
                </table>
            </div>
        </div>

        <div v-if="G" :class="['modal', { visible: rulesVisible }]">
            <div class="modal-content">
                <span class="close" @click="rulesVisible = false">&times;</span>
                <div class="modal-title">Rules Summary: {{ G.map.name }}</div>
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
                                        <template v-if="G.resourceResupplyNorth">
                                            (S), <strong>{{ G.resourceResupplyNorth[0] }}</strong> (N)
                                        </template>
                                    </li>
                                    <li v-if="G.map.uraniumMineResupply">
                                        Uranium market: remove
                                        <strong>{{ G.map.uraniumMineResupply[G.players.length - 2][0] }}</strong>
                                        token(s) from the cheapest slots
                                    </li>
                                    <li v-if="G.map.name === 'Manhattan'">
                                        Bureaucracy: move the <strong>two highest</strong> future-market plants to the
                                        discard pile (see Map Specific Rules for the full deck cycle)
                                    </li>
                                    <li v-else>Bureaucracy: remove <strong>highest</strong> power plant from market</li>
                                </ul>
                            </li>
                            <li v-if="G.map.name !== 'Manhattan'">
                                <strong>Step 2:</strong>
                                <ul>
                                    <li>
                                        Starts after building phase where a player has
                                        <strong>{{ G.citiesToStep2 }}</strong> or more cities
                                    </li>
                                    <li><strong>Two</strong> players per city</li>
                                    <li>
                                        Resource Resupply: <strong>{{ G.resourceResupply[1] }}</strong>
                                        <template v-if="G.resourceResupplyNorth">
                                            (S), <strong>{{ G.resourceResupplyNorth[1] }}</strong> (N)
                                        </template>
                                    </li>
                                    <li v-if="G.map.uraniumMineResupply">
                                        Uranium market: remove
                                        <strong>{{ G.map.uraniumMineResupply[G.players.length - 2][1] }}</strong>
                                        token(s) from the cheapest slots
                                    </li>
                                    <li>Bureaucracy: remove <strong>highest</strong> power plant from market</li>
                                </ul>
                            </li>
                            <li v-if="G.map.name !== 'Manhattan'">
                                <strong>Step 3:</strong>
                                <ul>
                                    <li>Starts after the "Step 3" card is drawn from the deck</li>
                                    <li><strong>Three</strong> players per city</li>
                                    <li>
                                        Resource Resupply: <strong>{{ G.resourceResupply[2] }}</strong>
                                        <template v-if="G.resourceResupplyNorth">
                                            (S), <strong>{{ G.resourceResupplyNorth[2] }}</strong> (N)
                                        </template>
                                    </li>
                                    <li v-if="G.map.uraniumMineResupply">
                                        Uranium market: remove
                                        <strong>{{ G.map.uraniumMineResupply[G.players.length - 2][2] }}</strong>
                                        token(s) from the cheapest slots
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
                            <span style="white-space: pre-wrap">{{ G.map.mapSpecificRules }}</span>
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
import type { GameState, Player } from 'powergrid-engine';
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
import { Phase, playerTimeUsed, PowerPlant, PowerPlantType, ResourceType } from 'powergrid-engine/src/gamestate';
import { City } from 'powergrid-engine/src/maps';
import { formatDuration } from '../util/time';

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

    defaultPlayerColors = ['limegreen', 'mediumorchid', 'red', 'dodgerblue', 'yellow', 'brown'];

    // Colors indexed by player id. Falls back to the default palette, but any color
    // a player drafted via the chooseColors option overrides their default entry.
    get playerColors() {
        const colors = [...this.defaultPlayerColors];
        if (this.G) {
            for (const p of this.G.players) {
                if (p.color) colors[p.id] = p.color;
            }
        }
        return colors;
    }

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

    freeJumpCity: City | null = null;
    freeJumpNormalPrice: number | null = null;
    freeJumpSlotPrice: number = 0;
    freeJumpVisible: boolean = false;

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
                }
                if (this.G.phase == Phase.Resources && !this.canPowerAllPlants(player)) {
                    this.confirmMessage = 'Are you sure you want to skip buying resources without enough to power all your plants?';
                    this.confirmVisible = true;
                    return;
                }

                if (
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

    buyResource(payload: { resource: ResourceType, side?: 'north' | 'south', fromStorage?: boolean }) {
        const data: { resource: ResourceType, side?: 'north' | 'south', fromStorage?: boolean } = { resource: payload.resource };
        if (payload.side) {
            data.side = payload.side;
        }
        if (payload.fromStorage) {
            data.fromStorage = payload.fromStorage;
        }
        this.sendMove({ name: MoveName.BuyResource, data });
    }

    bid(bid: number) {
        this.sendMove({ name: MoveName.Bid, data: bid });
    }

    build(city: City) {
        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;
        const buildMoves = availableMoves[MoveName.Build]!;
        const freeJumpMove = buildMoves.find((c) => c.name === city.name && c.freeJump);
        const normalMove = buildMoves.find((c) => c.name === city.name && !c.freeJump);

        if (freeJumpMove && normalMove) {
            // Player can choose: use the free jump or pay full price
            this.freeJumpCity = city;
            this.freeJumpSlotPrice = freeJumpMove.price;
            this.freeJumpNormalPrice = normalMove.price;
            this.freeJumpVisible = true;
        } else if (freeJumpMove && !normalMove) {
            // Only reachable via free jump — confirm before using it
            this.freeJumpCity = city;
            this.freeJumpSlotPrice = freeJumpMove.price;
            this.freeJumpNormalPrice = null;
            this.freeJumpVisible = true;
        } else {
            // Normal build, no free jump involved
            this.sendMove({ name: MoveName.Build, data: { name: city.name, price: normalMove!.price } });
        }
    }

    confirmFreeJump(useJump: boolean) {
        const city = this.freeJumpCity!;
        const currentPlayer = this.G!.players[this.player!];
        const buildMoves = currentPlayer.availableMoves![MoveName.Build]!;
        this.freeJumpVisible = false;
        this.freeJumpCity = null;
        if (useJump) {
            const freeJumpMove = buildMoves.find((c) => c.name === city.name && c.freeJump)!;
            this.sendMove({ name: MoveName.Build, data: { name: city.name, price: freeJumpMove.price, freeJump: true } });
        } else {
            const normalMove = buildMoves.find((c) => c.name === city.name && !c.freeJump)!;
            this.sendMove({ name: MoveName.Build, data: { name: city.name, price: normalMove.price } });
        }
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
                const coalDiscarded = parseInt(this.resourcesToDiscard[0].value);
                const oilDiscarded = parseInt(this.resourcesToDiscard[1].value);
                const newHybridCapacity = currentPlayer.hybridCapacity - this.discardedPowerPlant!.cost * 2;
                const coalInHybrid = Math.max(0, currentPlayer.coalLeft - currentPlayer.coalCapacity - coalDiscarded);
                const oilInHybrid = Math.max(0, currentPlayer.oilLeft - currentPlayer.oilCapacity - oilDiscarded);

                return newHybridCapacity < coalInHybrid + oilInHybrid;
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
            // Stamp the move so the engine can advance the per-player clocks. The
            // engine never reads the system clock itself — the timestamp lives in the
            // log so replaying a game reproduces the same times.
            this.emitter.emit('move', { ...move, time: Date.now() });
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

    buyableResources(): { resource: ResourceType, side?: 'north' | 'south', fromStorage?: boolean }[] {
        if (!this.canMove()) return [];

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        return availableMoves[MoveName.BuyResource] || [];
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

    getPickableRegions(): string[] {
        if (!this.canMove()) return [];

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        return availableMoves[MoveName.ChooseRegion] || [];
    }

    pickRegion(region: string) {
        this.sendMove({ name: MoveName.ChooseRegion, data: region });
    }

    canChooseColor() {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        return !!currentPlayer.availableMoves![MoveName.ChooseColor];
    }

    getChooseableColors(): string[] {
        if (!this.canMove()) return [];

        const currentPlayer = this.G!.players[this.player!];
        return currentPlayer.availableMoves![MoveName.ChooseColor] || [];
    }

    chooseColor(color: string) {
        this.sendMove({ name: MoveName.ChooseColor, data: color });
    }

    playerHasUsedFreeJump(playerIndex: number): boolean {
        const player = this.G?.players[playerIndex];
        if (!player) return false;
        if (player.usedFreeJump) return true;
        if (this.G?.log) {
            for (const entry of this.G.log) {
                if (entry.type === 'move' && (entry as any).player === playerIndex) {
                    const move = (entry as any).move;
                    if (move?.name === MoveName.Build && move?.data?.freeJump === true) {
                        return true;
                    }
                }
            }
        }
        return false;
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

    canPowerAllPlants(player: Player): boolean {
        // Calculate total resource requirements for all power plants
        let coalUsed = 0;
        let oilUsed = 0;
        let garbageUsed = 0;
        let uraniumUsed = 0;
        let hybridUsed = 0;
        for (const powerPlant of player.powerPlants) {
            switch (powerPlant.type) {
                case PowerPlantType.Coal:
                    coalUsed += powerPlant.cost;
                    break;
                case PowerPlantType.Oil:
                    oilUsed += powerPlant.cost;
                    break;
                case PowerPlantType.Garbage:
                    garbageUsed += powerPlant.cost;
                    break;
                case PowerPlantType.Uranium:
                    uraniumUsed += powerPlant.cost;
                    break;
                case PowerPlantType.Hybrid:
                    hybridUsed += powerPlant.cost;
                    break;
            }
        }

        // Check if player has enough resources, accounting for hybrid plants which can use either coal or oil
        if (coalUsed > player.coalLeft ||
            oilUsed > player.oilLeft ||
            garbageUsed > player.garbageLeft ||
            uraniumUsed > player.uraniumLeft) {
            return false;
        }
        const remainingCoal = player.coalLeft - coalUsed;
        const remainingOil = player.oilLeft - oilUsed;
        if (hybridUsed > remainingCoal + remainingOil) {
            return false;
        }
        return true;
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
        // Color draft (chooseColors): prompt the current picker, even on the very
        // first turn before any moves are in the log.
        if (
            this.G &&
            this.G.phase == Phase.ColorSelection &&
            this.player !== undefined &&
            this.G.currentPlayers.includes(this.player)
        ) {
            return 'Choose your color.';
        }

        // Region draft (chooseRegions): show the pick prompt to the current picker
        // even on the very first turn, before any moves are in the log.
        if (
            this.G &&
            this.G.phase == Phase.RegionSelection &&
            this.player !== undefined &&
            this.G.currentPlayers.includes(this.player)
        ) {
            const draft = this.G.regionDraft;
            return draft
                ? `Choose a region to play in (${draft.picked.length + 1} of ${draft.regionsNeeded}).`
                : 'Choose a region to play in.';
        }

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

    // Rows of the end-of-game Spending table, in display order.
    get spendingRows(): { label: string; value: (player: Player) => string | number }[] {
        return [
            { label: 'Income', value: (p) => p.totalIncome },
            { label: 'Spending: Cities', value: (p) => p.totalSpentCities },
            { label: 'Spending: Connections', value: (p) => p.totalSpentConnections },
            {
                // What each city on the board effectively cost: the house price plus
                // the connection cost paid to reach it, averaged over cities built.
                label: 'Cost per City',
                value: (p) =>
                    p.cities.length ? ((p.totalSpentCities + p.totalSpentConnections) / p.cities.length).toFixed(1) : '-',
            },
            { label: 'Spending: Plants', value: (p) => p.totalSpentPlants },
            { label: 'Spending: Resources', value: (p) => p.totalSpentResources },
            // Every clock is stopped once the game ends, so the banked total is final.
            { label: 'Time Used', value: (p) => formatDuration(playerTimeUsed(p)) },
        ];
    }

    get mapTransform() {
        if (!this.G?.map) return '';
        const [mx, my] = this.G.map.mapPosition!;
        const rotation = this.G.map.mapRotation;
        if (!rotation) return `translate(${mx}, ${my})`;
        const cities = this.G.map.cities;
        const xs = cities.map((c) => c.x);
        const ys = cities.map((c) => c.y);
        const cx = (Math.min(...xs) + Math.max(...xs)) / 2;
        const cy = (Math.min(...ys) + Math.max(...ys)) / 2;
        return `translate(${mx}, ${my}) rotate(${rotation}, ${cx}, ${cy})`;
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

    getResourceResupplyNorth() {
        if (this.G && this.G.resourceResupplyNorth) {
            let str = this.G.resourceResupplyNorth[this.G.step - 1];
            str = str.substr(1, str.length - 2);
            return str.split(',');
        }
        return null;
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
