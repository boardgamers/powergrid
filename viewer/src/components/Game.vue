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
        <svg id="scene" viewBox="0 0 1250 650" height="650">
            <rect width="100%" height="100%" x="0" y="0" fill="lightblue" />
            <rect width="100%" height="100" x="0" y="0" fill="gray" />
            <rect width="390" height="220" x="860" y="430" fill="gray" />

            <PassButton transform="translate(1105, 5)" :enabled="canPass()" @click="pass()" />
            <UndoButton transform="translate(1105, 36)" :enabled="canUndo()" @click="undo()" />
            <LogButton transform="translate(1105, 67)" @click="showLog()" />
            <SoundButton transform="translate(1200, 15)" :isOn="preferences.sound" @click="toggleSound()" />
            <HelpButton transform="translate(1200, 55)" :isOn="!preferences.disableHelp" @click="toggleHelp()" />

            <DropZone
                transform="translate(5, 5)"
                :width="600"
                :height="90"
                :enabled="true"
                :accepts="'container'"
                :data="{ type: 'supply' }"
                :availableMoves="getCurrentPlayerMoves()"
            />

            <template v-if="G">
                <template v-for="(p, i) in G.players">
                    <PlayerBoard
                        :key="'B' + i"
                        :player="p"
                        :color="playerColors[i]"
                        :transform="`translate(${250 * i}, 100)`"
                        :owner="i"
                        :isCurrentPlayer="isCurrentPlayer(i)"
                        :ended="gameEnded(G)"
                        @pieceDrop="onPieceDrop"
                    />
                    <rect
                        :key="'I' + i"
                        width="390"
                        height="41"
                        x="860"
                        :y="430 + i * 44"
                        fill="none"
                        stroke-width="3"
                        :stroke="playerColors[i]"
                    />
                </template>
            </template>

            <DropZone
                :transform="`translate(280, 425)`"
                :width="400"
                :height="225"
                :enabled="true"
                :accepts="'ship'"
                :data="{ type: 'openSea' }"
            />
            <DropZone
                :transform="`translate(770, 425)`"
                :width="480"
                :height="225"
                :enabled="true"
                :accepts="'ship'"
                :data="{ type: 'islandHarbor' }"
            />

            <template v-for="ship in ships">
                <Ship
                    :key="ship.id"
                    :pieceId="ship.id"
                    :targetState="{ x: ship.x, y: ship.y, rotate: ship.rotate }"
                    :canDrag="canDragShip(ship)"
                    :containers="ship.containers"
                    :owner="ship.owner"
                    :ownerName="G.players[ship.owner].name"
                    :position="ship.position"
                    :color="ship.color"
                />
            </template>

            <template v-for="container in containers">
                <Container
                    :key="container.id"
                    :pieceId="container.id"
                    :targetState="{
                        x: container.x,
                        y: container.y,
                        rotate: container.rotate,
                    }"
                    :canDrag="canDragContainer(container)"
                    :color="container.color"
                    :owner="container.owner"
                    :state="container.state"
                />
            </template>

            <template v-for="factory in factories">
                <Factory
                    :key="factory.id"
                    :pieceId="factory.id"
                    :targetState="{ x: factory.x, y: factory.y }"
                    :color="factory.color"
                    :canDrag="canDragFactory(factory)"
                />
            </template>

            <template v-for="warehouse in warehouses">
                <Warehouse
                    :key="warehouse.id"
                    :pieceId="warehouse.id"
                    :targetState="{ x: warehouse.x, y: warehouse.y }"
                    :canDrag="canDragWarehouse(warehouse)"
                />
            </template>

            <DropZone
                :transform="`translate(1045, 5)`"
                :width="50"
                :height="90"
                :enabled="true"
                :accepts="'loan'"
                :data="{ type: 'payLoan' }"
            />

            <template v-for="loanCard in loanCards">
                <LoanCard
                    :key="loanCard.id"
                    :targetState="{ x: loanCard.x, y: loanCard.y }"
                    :owner="loanCard.owner"
                    :player="player"
                    :canDrag="canDragLoan(loanCard)"
                    @fastClick="loan($event)"
                />
            </template>

            <template v-if="G && player != undefined">
                <text x="20" y="440">Money: ${{ G.players[player].money }}</text>
                <PointCard :pointCard="G.players[player].pointCard" transform="translate(20, 460)" />
            </template>

            <template v-if="isCurrentPlayer(player)">
                <template v-if="player == G.auctioningPlayer">
                    <template v-for="(bidder, i) in G.highestBidders">
                        <rect
                            v-if="!preferences.disableHelp"
                            :key="'R' + bidder"
                            x="139"
                            :y="449 + 40 * i"
                            width="132"
                            height="32"
                            fill="none"
                            stroke="blue"
                            stroke-width="2px"
                            rx="2px"
                        />
                        <Button
                            :key="bidder"
                            :transform="`translate(140, ${450 + 40 * i})`"
                            :width="130"
                            :text="'Accept ' + getName(bidder)"
                            @click="accept(bidder)"
                        />
                    </template>
                    <rect
                        v-if="!preferences.disableHelp"
                        x="139"
                        :y="449 + 40 * G.highestBidders.length"
                        width="132"
                        height="32"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />
                    <Button
                        :transform="`translate(140, ${450 + 40 * G.highestBidders.length})`"
                        :width="130"
                        :text="'Decline'"
                        :enabled="canDecline()"
                        @click="decline()"
                    />
                </template>
                <template v-else-if="G.phase == 'bid' && G.currentPlayers.includes(player)">
                    <rect
                        v-if="!preferences.disableHelp"
                        x="135"
                        y="425"
                        width="140"
                        height="220"
                        stroke="blue"
                        fill="transparent"
                        stroke-width="2px"
                        rx="2px"
                    />
                    <Calculator transform="translate(140, 430)" @bid="bid($event)" />
                </template>
            </template>

            <template v-if="G && gameEnded(G)">
                <Button
                    :transform="`translate(140, 580)`"
                    :width="130"
                    :text="'Final Score'"
                    @click="endScoreVisible = true"
                />
            </template>

            <template v-if="!preferences.disableHelp">
                <template v-if="ui.dragged == null">
                    <rect
                        v-if="canBuyFactory('orange')"
                        x="8"
                        y="8"
                        width="114"
                        height="24"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />
                    <rect
                        v-if="canBuyFactory('brown')"
                        x="128"
                        y="8"
                        width="114"
                        height="24"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />
                    <rect
                        v-if="canBuyFactory('white')"
                        x="248"
                        y="8"
                        width="114"
                        height="24"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />
                    <rect
                        v-if="canBuyFactory('darkslategray')"
                        x="368"
                        y="8"
                        width="114"
                        height="24"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />
                    <rect
                        v-if="canBuyFactory('tan')"
                        x="488"
                        y="8"
                        width="114"
                        height="24"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />

                    <rect
                        v-if="canBuyWarehouse()"
                        x="615"
                        y="10"
                        width="424"
                        height="72"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />

                    <rect
                        v-if="canProduce('orange')"
                        x="6"
                        y="36"
                        width="116"
                        height="54"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />
                    <rect
                        v-if="canProduce('brown')"
                        x="126"
                        y="36"
                        width="116"
                        height="54"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />
                    <rect
                        v-if="canProduce('white')"
                        x="246"
                        y="36"
                        width="116"
                        height="54"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />
                    <rect
                        v-if="canProduce('darkslategray')"
                        x="366"
                        y="36"
                        width="116"
                        height="54"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />
                    <rect
                        v-if="canProduce('tan')"
                        x="486"
                        y="36"
                        width="116"
                        height="54"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />

                    <rect
                        v-if="canGetLoan()"
                        x="1045"
                        y="5"
                        width="50"
                        height="90"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />

                    <rect
                        v-if="canPass()"
                        x="1104"
                        y="4"
                        width="82"
                        height="28"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />

                    <rect
                        v-if="canUndo()"
                        x="1104"
                        y="35"
                        width="82"
                        height="28"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />

                    <rect
                        v-if="canPayLoan()"
                        :x="200 + player * 250"
                        y="123"
                        width="47"
                        height="77"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />

                    <g v-if="canSail()">
                        <rect
                            v-if="!ships[player].rotate"
                            :x="ships[player].x - 5"
                            :y="ships[player].y - 5"
                            width="40"
                            height="90"
                            fill="none"
                            stroke="blue"
                            stroke-width="2px"
                            rx="2px"
                        />
                        <rect
                            v-else
                            :x="ships[player].x - 30"
                            :y="ships[player].y + 20"
                            width="90"
                            height="40"
                            fill="none"
                            stroke="blue"
                            stroke-width="2px"
                            rx="2px"
                        />
                    </g>

                    <rect
                        v-if="canArrangeFactory()"
                        :x="6 + player * 250"
                        y="158"
                        width="188"
                        height="44"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />

                    <rect
                        v-if="canArrangeWarehouse()"
                        :x="6 + player * 250"
                        y="248"
                        width="236"
                        height="44"
                        fill="none"
                        stroke="blue"
                        stroke-width="2px"
                        rx="2px"
                    />

                    <template v-if="G">
                        <template v-for="(p, i) in G.players">
                            <rect
                                v-if="canBuyFromPlayerFactory(p)"
                                :key="'PHF' + i"
                                :x="6 + i * 250"
                                y="158"
                                width="188"
                                height="44"
                                fill="none"
                                stroke="blue"
                                stroke-width="2px"
                                rx="2px"
                            />
                            <rect
                                v-if="canBuyFromPlayerWarehouse(p)"
                                :key="'PHW' + i"
                                :x="6 + i * 250"
                                y="248"
                                width="236"
                                height="44"
                                fill="none"
                                stroke="blue"
                                stroke-width="2px"
                                rx="2px"
                            />
                        </template>
                    </template>
                </template>
            </template>

            <use xlink:href="#moving" />
            <use xlink:href="#dragged" />
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

        <div v-if="G" :class="['modal', { visible: confirmBidVisible }]">
            <div class="modal-content">
                <div class="modal-title">Confirm total bid of ${{ totalBid }}?</div>
                <div style="text-align: center">
                    <button class="confirmButton" @click="confirmBid()">Confirm</button>
                    <button class="confirmButton" @click="confirmBidVisible = false">Cancel</button>
                </div>
            </div>
        </div>

        <div v-if="G" :class="['modal', { visible: confirmSailVisible }]">
            <div class="modal-content">
                <div class="modal-title">End your turn and start an auction?</div>
                <div style="text-align: center">
                    <button class="confirmButton" @click="confirmSail()">Confirm</button>
                    <button class="confirmButton" @click="confirmSailVisible = false">Cancel</button>
                </div>
            </div>
        </div>

        <div v-if="G" :class="['modal', { visible: endScoreVisible }]">
            <div class="modal-content">
                <span class="close" @click="endScoreVisible = false">&times;</span>
                <div class="modal-title">Final Score</div>
                <table class="final-score-table">
                    <tr>
                        <th><div>Player</div></th>
                        <th v-for="player in G.players" :key="'FS' + player.id">
                            <div :style="'background-color: ' + playerColors[player.id]">{{ player.name }}</div>
                        </th>
                    </tr>
                    <tr
                        v-for="(cat, i) in [
                            'Money',
                            '$10 containers',
                            '$5/$10 containers',
                            '$6 containers',
                            '$4 containers',
                            '$2 containers',
                            'Discarded color',
                            'Containers in Warehouses ($2 each)',
                            'Containers on Ship ($3 each)',
                            'Loans (-$11 each)',
                        ]"
                        :key="'FC_' + cat"
                    >
                        <td>{{ cat }}</td>
                        <td v-for="player in G.players" :key="'FS' + player.id + i">
                            <div
                                :style="i === 6 || i === 9 ? 'color: red;' : 'color: green;'"
                                v-html="getFinalScoreHTML(player, i)"
                            />
                        </td>
                    </tr>
                    <tr>
                        <td>Final Score</td>
                        <td v-for="player in G.players" :key="'FS' + player.id + 'money'">
                            <div style="font-weight: bold" :style="player.money < 0 ? 'color: red;' : 'color: green;'">
                                {{ player.money > 0 ? '$' + player.money : '-$' + Math.abs(player.money) }}
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
import { MoveName, ended, move as engineMove } from 'container-engine';
import type { GameState } from 'container-engine';
import { EventEmitter } from 'events';
import { groupBy } from 'lodash';
import { ContainerState, DropZoneType, Piece, PieceType, ShipType, UIData, Preferences } from '../types/ui-data';
import { ContainerColor, ShipPosition } from 'container-engine/src/gamestate';
import { Container, Factory, Warehouse, Ship, LoanCard, Piece as PieceComponent } from './pieces';
import { Button, PassButton, UndoButton, LogButton, SoundButton, HelpButton } from './buttons';
import PlayerBoard from './PlayerBoard.vue';
import PointCard from './PointCard.vue';
import DropZone from './DropZone.vue';
import Calculator from './Calculator.vue';
import { GameEventName, LogMove } from 'container-engine/src/log';

@Component({
    created(this: Game) {
        this.communicator.on('pieceDrop', this.onPieceDrop);
        this.$on('hook:beforeDestroy', () => this.communicator.off('pieceDrop', this.onPieceDrop));
    },
    components: {
        PlayerBoard,
        Container,
        Factory,
        Warehouse,
        LoanCard,
        PointCard,
        Ship,
        PassButton,
        UndoButton,
        LogButton,
        SoundButton,
        HelpButton,
        DropZone,
        Calculator,
        Button,
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
        dragged: null,
        waitingAnimations: 0,
    };

    @Provide()
    communicator: EventEmitter = new EventEmitter();

    @ProvideReactive()
    G?: GameState | null = null;

    // Pieces
    containers: Piece[] = [];
    factories: Piece[] = [];
    warehouses: Piece[] = [];
    warehousesBuilt: Piece[] = [];
    loanCards: Piece[] = [];
    ships: ShipType[] = [];

    playerColors = ['dodgerblue', 'red', 'yellow', 'limegreen', 'mediumorchid'];

    animationQueue: Array<Function> = [];

    logVisible = false;
    endScoreVisible = false;
    confirmBidVisible = false;
    confirmSailVisible = false;

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
                if (
                    move.name == MoveName.DomesticSale ||
                    move.name == MoveName.BuyWarehouse ||
                    move.name == MoveName.ArrangeWarehouse ||
                    move.name == MoveName.BuyFactory ||
                    move.name == MoveName.BuyFromFactory ||
                    move.name == MoveName.Produce ||
                    move.name == MoveName.Sail ||
                    move.name == MoveName.ArrangeFactory
                ) {
                    setTimeout(() => {
                        (document.getElementById('piece-drop')!.cloneNode(true) as HTMLAudioElement).play();
                    }, 800);
                } else if (
                    move.name == MoveName.Accept ||
                    move.name == MoveName.Decline ||
                    move.name == MoveName.BuyFromWarehouse
                ) {
                    (document.getElementById('piece-drop')!.cloneNode(true) as HTMLAudioElement).play();
                }
            }
        }
    }

    createPieces() {
        // Containers
        this.containers = [];
        this.G?.players.forEach((player, pi) => {
            let grouped = groupBy(player.containersOnFactoryStore, (c) => c.price);
            Object.keys(grouped).forEach((price) => {
                grouped[price].forEach((container, ci) => {
                    this.containers.push({
                        id: container.piece.id,
                        x: 8 + pi * 250 + (container.price - 1) * 48 + (ci % 2) * 20,
                        y: 160 + Math.floor(ci / 2) * 10,
                        rotate: 0,
                        color: container.piece.color.toString(),
                        owner: pi,
                        state: ContainerState.OnFactoryStore,
                    });
                });
            });

            grouped = groupBy(player.containersOnWarehouseStore, (c) => c.price);
            Object.keys(grouped).forEach((price) => {
                grouped[price].forEach((container, ci) => {
                    this.containers.push({
                        id: container.piece.id,
                        x: 8 + pi * 250 + (container.price - 2) * 48 + (ci % 2) * 20,
                        y: 250 + Math.floor(ci / 2) * 10,
                        rotate: 0,
                        color: container.piece.color.toString(),
                        owner: pi,
                        state: ContainerState.OnWarehouseStore,
                    });
                });
            });

            let lastColor;
            let offset = 0;
            player.containersOnIsland
                .sort((a, b) => a.color.localeCompare(b.color))
                .forEach((container, ci) => {
                    if (container.color !== lastColor) offset += 10;

                    if (player.containersOnIsland.length <= 28) {
                        this.containers.push({
                            id: container.id,
                            x: 860 + offset + 12 * ci,
                            y: 445 + 44 * pi,
                            rotate: 90,
                            color: container.color.toString(),
                            owner: pi,
                            state: ContainerState.OnIsland,
                        });
                    } else {
                        this.containers.push({
                            id: container.id,
                            x: 860 + offset + 6 * ci,
                            y: 435 + 44 * pi + 20 * (ci % 2),
                            rotate: 90,
                            color: container.color.toString(),
                            owner: pi,
                            state: ContainerState.OnIsland,
                        });
                    }

                    lastColor = container.color;
                });
        });

        if (this.G?.containersLeft) {
            let c = {};
            this.G?.containersLeft.sort().forEach((container) => {
                if (!c[container.color]) {
                    c[container.color] = 0;
                }

                const offset = 120 * Object.values(ContainerColor).indexOf(container.color);
                this.containers.push({
                    id: container.id,
                    x: 10 + offset + 22 * (c[container.color] % 5),
                    y: 40 + Math.floor(c[container.color] / 5) * 12,
                    rotate: 0,
                    color: container.color.toString(),
                    owner: -1,
                    state: ContainerState.OnBoard,
                });

                c[container.color]++;
            });
        }

        // Factories
        this.factories = [];
        this.G?.players.forEach((player, pi) => {
            player.factories.forEach((factory, i) => {
                this.factories.push({
                    id: factory.id,
                    x: 28 + pi * 250 + i * 48,
                    y: 140,
                    owner: player.id,
                    color: factory.color.toString(),
                });
            });
        });

        if (this.G?.factoriesLeft) {
            let c = 0;
            let lastColor;
            this.G?.factoriesLeft.sort().forEach((factory) => {
                if (lastColor !== factory.color) {
                    c = 0;
                }

                const offset = 120 * Object.values(ContainerColor).indexOf(factory.color);
                this.factories.push({
                    id: factory.id,
                    x: 20 + offset + 22 * (c % 5),
                    y: 20 + Math.floor(c / 5) * 12,
                    owner: -1,
                    color: factory.color.toString(),
                });
                lastColor = factory.color;
                c++;
            });
        }

        // Warehouses
        this.warehouses = [];
        this.G?.players.forEach((player, pi) => {
            for (let c = 0; c < player.warehouses.length; c++) {
                this.warehouses.push({
                    id: player.warehouses[c].id,
                    x: 13 + pi * 250 + c * 48,
                    y: 210,
                    owner: player.id,
                });
            }
        });

        if (this.G?.warehousesLeft) {
            for (let c = 0; c < this.G.warehousesLeft.length; c++) {
                this.warehouses.push({
                    id: this.G.warehousesLeft[c].id,
                    x: 620 + 32 * (c % 13),
                    y: 15 + Math.floor(c / 13) * 32,
                    owner: -1,
                });
            }
        }

        // Loan Cards
        this.loanCards = [];
        this.G?.loansLeft.forEach((loan, i) => {
            this.loanCards.push({ id: loan.id, x: 1050 + i, y: 29 - i * 2, owner: -1 });
        });

        this.G?.players.forEach((player, pi) => {
            player.loans.forEach((loan, c) => {
                this.loanCards.push({ id: loan.id, x: 205 + pi * 250 + c * 7, y: 135 - c * 7, owner: player.id });
            });
        });

        // Ships
        this.ships = [];
        this.G?.players.forEach((player, pi) => {
            const color = ['dodgerblue', 'red', 'yellow', 'limegreen', 'mediumorchid'][pi];
            switch (player.ship.shipPosition) {
                case ShipPosition.OpenSea:
                    this.ships.push({
                        id: player.ship.piece.id,
                        x: 380 + pi * 44,
                        y: 480,
                        rotate: 0,
                        color,
                        containers: player.ship.containers,
                        owner: pi,
                        position: player.ship.shipPosition,
                    });
                    break;

                case ShipPosition.Island:
                    this.ships.push({
                        id: player.ship.piece.id,
                        x: 800,
                        y: 410 + pi * 44,
                        rotate: 90,
                        color,
                        containers: player.ship.containers,
                        owner: pi,
                        position: player.ship.shipPosition,
                    });
                    break;

                default:
                    const otherPlayer = Number.parseInt(player.ship.shipPosition[12]);
                    const harbor = Number.parseInt(player.ship.shipPosition[13]);
                    this.ships.push({
                        id: player.ship.piece.id,
                        x: 26 + 250 * otherPlayer + 62 * (harbor - 1),
                        y: 305,
                        rotate: 0,
                        color,
                        containers: player.ship.containers,
                        owner: pi,
                        position: player.ship.shipPosition,
                    });
                    break;
            }
        });
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

    onPieceDrop(e: PieceComponent, d: any) {
        const currentPlayer = this.G!.currentPlayers[0];
        switch (e.pieceType) {
            case PieceType.Warehouse:
                this.sendMove({ name: MoveName.BuyWarehouse, data: true, extraData: { id: e.pieceId } });
                break;

            case PieceType.Factory:
                const factory = e as Factory;
                this.sendMove({
                    name: MoveName.BuyFactory,
                    data: factory.color,
                    extraData: { id: factory.pieceId, color: factory.color },
                });
                break;

            case PieceType.Container:
                const container = e as Container;
                if (container.state == ContainerState.OnBoard) {
                    if (d.type == DropZoneType.FactoryStore) {
                        this.sendMove({
                            name: MoveName.Produce,
                            data: container.color,
                            extraData: { piece: { id: container.pieceId, color: container.color }, price: d.price },
                        });
                    }
                } else if (container.state == ContainerState.OnFactoryStore) {
                    if (d.type == DropZoneType.FactoryStore) {
                        if (
                            this.G!.players[currentPlayer].containersOnFactoryStore.find(
                                (c) => c.piece.id == e.pieceId
                            )!.price === d.price
                        ) {
                            return;
                        }

                        this.sendMove({
                            name: MoveName.ArrangeFactory,
                            data: { id: container.pieceId, color: container.color },
                            extraData: { price: d.price },
                        });
                    } else if (d.type == DropZoneType.WarehouseStore) {
                        this.sendMove({
                            name: MoveName.BuyFromFactory,
                            data: { player: container.owner, piece: { id: container.pieceId, color: container.color } },
                            extraData: { price: d.price },
                        });
                    } else if (d.type == DropZoneType.Supply) {
                        this.sendMove({
                            name: MoveName.DomesticSale,
                            data: { id: container.pieceId, color: container.color },
                        });
                    }
                } else if (container.state == ContainerState.OnWarehouseStore) {
                    if (d.type == DropZoneType.WarehouseStore) {
                        if (
                            this.G!.players[currentPlayer].containersOnWarehouseStore.find(
                                (c) => c.piece.id == e.pieceId
                            )!.price === d.price
                        ) {
                            return;
                        }

                        this.sendMove({
                            name: MoveName.ArrangeWarehouse,
                            data: { id: container.pieceId, color: container.color },
                            extraData: { price: d.price },
                        });
                    } else if (d.type == DropZoneType.Ship) {
                        this.sendMove({
                            name: MoveName.BuyFromWarehouse,
                            data: { player: container.owner, piece: { id: container.pieceId, color: container.color } },
                        });
                    } else if (d.type == DropZoneType.Supply) {
                        this.sendMove({
                            name: MoveName.DomesticSale,
                            data: { id: container.pieceId, color: container.color },
                        });
                    }
                }

                break;

            case PieceType.Ship:
                const player = this.G!.players[currentPlayer];
                if (d.type.startsWith('playerHarbor')) {
                    if (!player.ship.shipPosition.startsWith('playerHarbor'))
                        this.sendMove({ name: MoveName.Sail, data: d.type });
                } else if (d.type === DropZoneType.OpenSea) {
                    if (player.ship.shipPosition !== ShipPosition.OpenSea)
                        this.sendMove({ name: MoveName.Sail, data: ShipPosition.OpenSea });
                } else if (d.type === DropZoneType.IslandHarbor) {
                    if (player.ship.shipPosition !== ShipPosition.Island) {
                        this.confirmSailVisible = true;
                    }
                }

                break;

            case PieceType.Loan:
                const loan = e as LoanCard;
                if (loan.owner == -1 && d.type == DropZoneType.GetLoan) {
                    this.sendMove({ name: MoveName.GetLoan, data: true });
                } else if (loan.owner !== -1 && d.type == DropZoneType.PayLoan) {
                    this.sendMove({ name: MoveName.PayLoan, data: true });
                }

                break;
        }

        this.updateUI();
    }

    getName(bidder) {
        return this.G!.players[bidder].name;
    }

    pass() {
        this.sendMove({ name: MoveName.Pass, data: true });
    }

    undo() {
        this.sendMove({ name: MoveName.Undo, data: true });
    }

    loan(event) {
        const loan = event as LoanCard;
        if (loan.owner == -1) {
            this.sendMove({ name: MoveName.GetLoan, data: true });
        } else if (loan.owner == this.player) {
            this.sendMove({ name: MoveName.PayLoan, data: true });
        }
    }

    bid(event) {
        if (this.G!.players[this.player!].bid != 0) {
            this.confirmBidVisible = true;
            this.totalBid = this.G!.players[this.player!].bid + event;
        } else {
            this.sendMove({ name: MoveName.Bid, data: true, extraData: { price: event } });
        }
    }

    confirmBid() {
        this.confirmBidVisible = false;
        this.sendMove({ name: MoveName.Bid, data: true, extraData: { price: this.totalBid - this.G!.players[this.player!].bid } });
        this.totalBid = 0;
    }

    confirmSail() {
        this.confirmSailVisible = false;
        this.sendMove({ name: MoveName.Sail, data: ShipPosition.Island });
    }

    accept(bidder) {
        this.sendMove({ name: MoveName.Accept, data: bidder });
    }

    decline() {
        this.sendMove({ name: MoveName.Decline, data: true });
    }

    sendMove(move) {
        this.emitter.emit('move', move);

        this.replaceState(engineMove(this.G!, move, this.player!, true), true);
    }

    gameEnded(G: GameState) {
        return ended(G);
    }

    canMove() {
        return (
            this.player &&
            this.G &&
            this.G.currentPlayers.includes(this.player!) &&
            this.G.players[this.player!] &&
            this.G.players[this.player!].availableMoves
        );
    }

    canDragContainer(container: Piece) {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        switch (container.state) {
            case ContainerState.OnBoard: {
                const available = availableMoves[MoveName.Produce];
                return (
                    available &&
                    available.indexOf(container.color as ContainerColor) != -1 &&
                    currentPlayer.produced.indexOf(container.color as ContainerColor) == -1
                );
            }

            case ContainerState.OnFactoryStore: {
                if (container.owner == currentPlayer.id) {
                    return (
                        availableMoves[MoveName.ArrangeFactory]?.find((c) => c.id == container.id) ||
                        availableMoves[MoveName.DomesticSale]?.find((c) => c.id == container.id)
                    );
                } else {
                    return availableMoves[MoveName.BuyFromFactory]?.find((a) => a.piece.id == container.id);
                }
            }

            case ContainerState.OnWarehouseStore: {
                if (container.owner == currentPlayer.id) {
                    return (
                        availableMoves[MoveName.ArrangeWarehouse]?.find((c) => c.id == container.id) ||
                        availableMoves[MoveName.DomesticSale]?.find((c) => c.id == container.id)
                    );
                } else {
                    return availableMoves[MoveName.BuyFromWarehouse]?.find((a) => a.piece.id == container.id);
                }
            }

            case ContainerState.OnShip:
            case ContainerState.OnIsland:
            default:
                return false;
        }
    }

    canDragFactory(factory: Piece) {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        if (factory.owner !== -1) return false;

        const available = availableMoves[MoveName.BuyFactory];
        return available && available.find((a) => a == factory.color);
    }

    canDragWarehouse(warehouse: Piece) {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        if (warehouse.owner !== -1) return false;

        return availableMoves[MoveName.BuyWarehouse] != undefined;
    }

    canDragLoan(loanCard: Piece) {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        if (loanCard.owner == -1) {
            return availableMoves[MoveName.GetLoan] != undefined;
        } else if (loanCard.owner == currentPlayer.id) {
            return availableMoves[MoveName.PayLoan] != undefined;
        }

        return false;
    }

    canDragShip(ship: Piece) {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        return availableMoves[MoveName.Sail] && this.isCurrentPlayer(ship.owner);
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

    canDecline() {
        if (!this.canMove()) return false;

        const currentPlayer = this.G!.players[this.player!];
        const availableMoves = currentPlayer.availableMoves!;

        return !!availableMoves[MoveName.Decline];
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
            if (this.G.players[this.player].availableMoves![MoveName.Bid]) {
                if (this.G.highestBidders.length != 0) {
                    return 'It\'s a tie, choose your ADDITIONAL bid!';
                }

                return 'It\'s your turn to bid!';
            }

            return 'It\'s your turn!';
        } else {
            if (
                !this.G.log ||
                this.G.log.length == 0 ||
                this.G.log[this.G.log.length - 1].type != 'move' ||
                (this.G.log[this.G.log.length - 1] as LogMove).move.name == MoveName.Pass
            )
                return `Waiting for ${this.G!.currentPlayers.map(p => this.G?.players[p].name).join(', ')} to play...`;

            let log = (this.G.log[this.G.log.length - 1] as LogMove).pretty;
            while (log?.indexOf('>') != -1) {
                log = log?.substr(0, log.indexOf('<')) + log.substr(log.indexOf('>') + 1);
            }

            return log.replaceAll('darkslategray', 'dark green');
        }
    }

    isCurrentPlayer(player) {
        return this.G && this.G.currentPlayers.includes(player);
    }

    canBuyFactory(color) {
        return (
            this.G &&
            this.G.currentPlayers.includes(this.player!) &&
            this.G.players[this.player!] &&
            this.G.players[this.player!].availableMoves &&
            this.G.players[this.player!].availableMoves![MoveName.BuyFactory] &&
            this.G.players[this.player!].availableMoves![MoveName.BuyFactory]!.indexOf(color) != -1
        );
    }

    canBuyWarehouse() {
        return (
            this.G &&
            this.G.currentPlayers.includes(this.player!) &&
            this.G.players[this.player!] &&
            this.G.players[this.player!].availableMoves &&
            this.G.players[this.player!].availableMoves![MoveName.BuyWarehouse]
        );
    }

    canProduce(color) {
        return (
            this.G &&
            this.G.currentPlayers.includes(this.player!) &&
            this.G.players[this.player!] &&
            this.G.players[this.player!].availableMoves &&
            this.G.players[this.player!].availableMoves![MoveName.Produce] &&
            this.G.players[this.player!].availableMoves![MoveName.Produce]!.indexOf(color) != -1
        );
    }

    canGetLoan() {
        return (
            this.G &&
            this.G.currentPlayers.includes(this.player!) &&
            this.G.players[this.player!] &&
            this.G.players[this.player!].availableMoves &&
            this.G.players[this.player!].availableMoves![MoveName.GetLoan]
        );
    }

    canPayLoan() {
        return (
            this.G &&
            this.G.currentPlayers.includes(this.player!) &&
            this.G.players[this.player!] &&
            this.G.players[this.player!].availableMoves &&
            this.G.players[this.player!].availableMoves![MoveName.PayLoan]
        );
    }

    canSail() {
        return (
            this.G &&
            this.G.currentPlayers.includes(this.player!) &&
            this.G.players[this.player!] &&
            this.G.players[this.player!].availableMoves &&
            this.G.players[this.player!].availableMoves![MoveName.Sail]
        );
    }

    canArrangeFactory() {
        return (
            this.G &&
            this.G.currentPlayers.includes(this.player!) &&
            this.G.players[this.player!] &&
            this.G.players[this.player!].availableMoves &&
            this.G.players[this.player!].availableMoves![MoveName.ArrangeFactory]
        );
    }

    canArrangeWarehouse() {
        return (
            this.G &&
            this.G.currentPlayers.includes(this.player!) &&
            this.G.players[this.player!] &&
            this.G.players[this.player!].availableMoves &&
            this.G.players[this.player!].availableMoves![MoveName.ArrangeWarehouse]
        );
    }

    canBuyFromPlayerFactory(otherPlayer) {
        if (
            this.G &&
            this.G.currentPlayers.includes(this.player!) &&
            this.G.players[this.player!] &&
            this.G.players[this.player!].availableMoves &&
            this.G.players[this.player!].availableMoves![MoveName.BuyFromFactory]
        ) {
            const buyable = this.G.players[this.player!].availableMoves![MoveName.BuyFromFactory]!.map(
                (c) => c.piece.id
            );
            const playerContainers = otherPlayer.containersOnFactoryStore.map((c) => c.piece.id);
            return buyable.some((id) => playerContainers.indexOf(id) !== -1);
        }

        return false;
    }

    canBuyFromPlayerWarehouse(otherPlayer) {
        if (
            this.G &&
            this.G.currentPlayers.includes(this.player!) &&
            this.G.players[this.player!] &&
            this.G.players[this.player!].availableMoves &&
            this.G.players[this.player!].availableMoves![MoveName.BuyFromWarehouse]
        ) {
            const buyable = this.G.players[this.player!].availableMoves![MoveName.BuyFromWarehouse]!.map(
                (c) => c.piece.id
            );
            const playerContainers = otherPlayer.containersOnWarehouseStore.map((c) => c.piece.id);
            return buyable.some((id) => playerContainers.indexOf(id) !== -1);
        }

        return false;
    }

    isDragging(pieceType) {
        return this.ui && this.ui.dragged != null && this.ui.dragged.pieceType == pieceType;
    }

    draggedContainerType() {
        if (this.ui && this.ui.dragged != null && this.ui.dragged.pieceType == 'container') {
            const container = this.ui.dragged as Container;

            if (container.owner == this.player) {
                if (container.state == ContainerState.OnFactoryStore) {
                    return 'ownFactoryContainer';
                } else if (container.state == ContainerState.OnWarehouseStore) {
                    return 'ownWarehouseContainer';
                }
            } else {
                if (container.state == ContainerState.OnBoard) {
                    return 'boardContainer';
                } else if (container.state == ContainerState.OnFactoryStore) {
                    return 'factoryContainer';
                } else if (container.state == ContainerState.OnWarehouseStore) {
                    return 'warehouseContainer';
                }
            }
        }

        return null;
    }

    get logReversed() {
        let logReversed: string[] = [];
        if (this.G && this.G.log) {
            this.G.log.forEach((log) => {
                if (log.type == 'phase') {
                    logReversed.push('New phase: ' + log.phase);
                } else if (log.type == 'event') {
                    if (log.event.name == GameEventName.Upkeep) {
                        logReversed.push('New event: ' + log.event.interest);
                    } else {
                        logReversed.push('New event: ' + log.event.name);
                    }
                } else if (log.type == 'move') {
                    logReversed.push(log.pretty.replaceAll('darkslategray', 'dark green'));
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
                if (log.type == 'phase') {
                    logReversed.push('New phase: ' + log.phase);
                } else if (log.type == 'event') {
                    if (log.event.name == GameEventName.Upkeep) {
                        logReversed.push('New event: ' + log.event.interest);
                    } else {
                        logReversed.push('New event: ' + log.event.name);
                    }
                } else if (log.type == 'move') {
                    logReversed.push(log.simple.replaceAll('darkslategray', 'dark green'));
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

    getCurrentPlayerMoves() {
        if (!this.canMove())
            return [];

        return this.G!.players[this.player!].availableMoves!;
    }

    getFinalScoreHTML(player, i) {
        let str = player.finalScoreBreakdown ? player.finalScoreBreakdown[i] : '0';

        str = str.replaceAll('brown', '<span style="font-weight: bold; border: 1px solid black; padding: 0 12px; font-size: 12px; background-color: brown; color: brown;"></span>');
        str = str.replaceAll('darkslategray', '<span style="font-weight: bold; border: 1px solid black; padding: 0 12px; font-size: 12px; background-color: darkslategray; color: darkslategray;"></span>');
        str = str.replaceAll('orange', '<span style="font-weight: bold; border: 1px solid black; padding: 0 12px; font-size: 12px; background-color: orange; color: orange;"></span>');
        str = str.replaceAll('tan', '<span style="font-weight: bold; border: 1px solid black; padding: 0 12px; font-size: 12px; background-color: tan; color: tan;"></span>');
        str = str.replaceAll('white', '<span style="font-weight: bold; border: 1px solid black; padding: 0 12px; font-size: 12px; background-color: white; color: white;"></span>');

        return str;
    }
}
</script>
<style lang="scss">
.game {
    height: 100%;
    background-color: lightblue;
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

.piece {
    &:not(.dragging) {
        transition: transform 0.8s ease-in-out;
    }

    &.canDrag {
        cursor: pointer;

        &:hover {
            & > circle,
            & > rect,
            & > path {
                stroke: white;
            }
        }
    }
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
    padding-top: 100px; /* Location of the box */
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
    max-height: calc(100% - 42px);
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
