<template>
    <g @click="onPickCoord">
        <!-- Dev-only backdrop for coord-picking. See GameMap.devBackdrop. -->
        <image
            v-if="devBackdrop"
            :href="devBackdrop.src"
            x="0"
            y="0"
            :width="devBackdrop.width"
            :height="devBackdrop.height"
            :opacity="devBackdrop.opacity != null ? devBackdrop.opacity : 0.5"
        />

        <!-- <template v-for="polygon in polygons">
            <polygon
                :key="'pol_ ' + polygon.region"
                :points="polygon.points.map((p) => `${p[0]},${p[1]}`).join(' ')"
                :fill="polygon.region"
                opacity="0.8"
                stroke="black"
            ></polygon>
        </template> -->

        <template v-for="city in cities">
            <circle
                v-if="city.connectionCost == null"
                :key="city.name + '_region'"
                r="25"
                :cx="city.x"
                :cy="city.y"
                :fill="city.region"
                stroke="black"
            >
                <title>{{ city.name }}</title>
            </circle>
            <circle
                v-if="city.connectionCost == null"
                :key="city.name + '_circle'"
                r="20"
                :cx="city.x"
                :cy="city.y"
                fill="gray"
                stroke="black"
            >
                <title>{{ city.name }}</title>
            </circle>
            <!-- South Africa cross-border spaces: render a small red pennant
                 above the city. Marks a single-occupancy space ($30 total cost). -->
            <g v-if="city.singleOccupancy" :key="city.name + '_flag'">
                <line
                    :x1="city.x + 12"
                    :y1="city.y - 12"
                    :x2="city.x + 12"
                    :y2="city.y - 32"
                    stroke="black"
                    stroke-width="1.5"
                />
                <polygon
                    :points="`${city.x + 12},${city.y - 32} ${city.x + 26},${city.y - 28} ${city.x + 12},${
                        city.y - 24
                    }`"
                    fill="red"
                    stroke="black"
                    stroke-width="1"
                />
                <title>{{ city.name }} — cross-border space (1 house max, 30 Elektro total cost)</title>
            </g>
        </template>

        <template v-for="connection in connections">
            <line
                :key="connection.nodes[0] + '_' + connection.nodes[1] + '_line1'"
                :x1="getX1(connection)"
                :y1="getY1(connection)"
                :x2="getX2(connection)"
                :y2="getY2(connection)"
                stroke-width="10"
                stroke="black"
            />
            <line
                :key="connection.nodes[0] + '_' + connection.nodes[1] + '_line2'"
                :x1="getX1(connection)"
                :y1="getY1(connection)"
                :x2="getX2(connection)"
                :y2="getY2(connection)"
                stroke-width="9"
                stroke="gray"
            />
        </template>

        <!-- Bremen-style node-weighted districts: clean labeled tiles (entry-cost
             number + 8/14/20 house slots), drawn AFTER the links so the gray lines
             sit behind. Gated on connectionCost; other maps keep circular nodes. -->
        <template v-for="city in cities">
            <g
                v-if="city.connectionCost != null && city.slotCosts && city.slotCosts.length >= 2"
                :key="city.name + '_tile'"
            >
                <rect
                    :class="[{ canClick: canBuild(city) || canPickRegion(city) }]"
                    :x="city.x - 23"
                    :y="city.y - 23"
                    width="46"
                    height="46"
                    rx="7"
                    fill="gray"
                    :stroke="city.region"
                    stroke-width="4"
                    :transform="`rotate(45, ${city.x}, ${city.y})`"
                    @click="onCityClick(city)"
                >
                    <title>{{ city.name }} — connect for {{ city.connectionCost }} (entry) + house</title>
                </rect>
                <!-- house slots laid out like the board: 8 top, 14 left, 20 right -->
                <template v-for="(sc, i) in city.slotCosts">
                    <rect
                        :key="city.name + '_slot' + i"
                        :x="city.x + nodeSlotPos(i).dx - 6.5"
                        :y="city.y + nodeSlotPos(i).dy - 6.5"
                        width="13"
                        height="13"
                        rx="1"
                        fill="gray"
                        stroke="black"
                        stroke-width="1"
                        :transform="`rotate(45, ${city.x + nodeSlotPos(i).dx}, ${city.y + nodeSlotPos(i).dy})`"
                    />
                    <text
                        :key="city.name + '_slotlbl' + i"
                        :x="city.x + nodeSlotPos(i).dx"
                        :y="city.y + nodeSlotPos(i).dy"
                        font-size="10"
                        text-anchor="middle"
                        dominant-baseline="central"
                        fill="black"
                        :transform="
                            mapRotation
                                ? `rotate(${-mapRotation}, ${city.x + nodeSlotPos(i).dx}, ${
                                      city.y + nodeSlotPos(i).dy
                                  })`
                                : undefined
                        "
                    >
                        {{ sc }}
                    </text>
                </template>
            </g>
        </template>

        <!-- Manhattan single-house spaces: one house per space at its printed price.
             Small, semi-transparent tile (no entry-cost circle — connection is a flat
             5 everywhere, stated in the rules) so the price reads cleanly and tiles
             never hide the board beneath when they overlap. -->
        <template v-for="city in cities">
            <g
                v-if="city.connectionCost != null && city.slotCosts && city.slotCosts.length === 1"
                :key="city.name + '_mtile'"
            >
                <rect
                    :class="[{ canClick: canBuild(city) }]"
                    :x="city.x - 13"
                    :y="city.y - 13"
                    width="26"
                    height="26"
                    rx="5"
                    :fill="isBlocked(city) ? '#555555' : 'white'"
                    :fill-opacity="isBlocked(city) ? 0.88 : 0.82"
                    stroke="black"
                    stroke-width="1.5"
                    @click="canBuild(city) && build(city)"
                >
                    <title>
                        {{ city.name }}<template v-if="isBlocked(city)"> — blocked for this player count (transit
                        only)</template ><template v-else> — build for {{ city.slotCosts[0] }} (+ flat 5 per transited
                        space)</template>
                    </title>
                </rect>
                <text
                    :x="city.x"
                    :y="city.y"
                    font-size="17"
                    font-weight="bold"
                    text-anchor="middle"
                    dominant-baseline="central"
                    :fill="isBlocked(city) ? '#dddddd' : 'black'"
                >
                    {{ city.slotCosts[0] }}
                </text>
            </g>
        </template>

        <template v-for="city in cities">
            <circle
                v-if="city.connectionCost == null"
                :key="city.name + '_circle2'"
                :class="[{ canClick: canBuild(city) || canPickRegion(city) }]"
                r="20"
                :cx="city.x"
                :cy="city.y"
                fill="gray"
                @click="onCityClick(city)"
            >
                <title>{{ city.name }}</title>
            </circle>
        </template>

        <template v-for="connection in connections">
            <circle
                v-if="connection.cost > 0"
                :key="connection.nodes[0] + '_' + connection.nodes[1] + '_border'"
                stroke="black"
                :r="10 + (connection.cost * 10) / 28"
                :cx="(getX1(connection) + getX2(connection)) / 2"
                :cy="(getY1(connection) + getY2(connection)) / 2"
                :fill="connection.cost > 15 ? 'gold' : connection.cost > 10 ? 'lightgray' : 'tan'"
            />
            <circle
                v-if="connection.cost > 0"
                :key="connection.nodes[0] + '_' + connection.nodes[1] + '_circle'"
                :r="6 + (connection.cost * 10) / 28"
                :cx="(getX1(connection) + getX2(connection)) / 2"
                :cy="(getY1(connection) + getY2(connection)) / 2"
                fill="gray"
                stroke="black"
            />
            <text
                v-if="connection.cost > 0"
                :key="connection.nodes[0] + '_' + connection.nodes[1] + '_text'"
                text-anchor="middle"
                :style="`font-size: ${12 + (connection.cost * 6) / 28}px`"
                fill="black"
                :x="(getX1(connection) + getX2(connection)) / 2"
                :y="(getY1(connection) + getY2(connection)) / 2"
                :transform="
                    mapRotation
                        ? `rotate(${-mapRotation}, ${(getX1(connection) + getX2(connection)) / 2}, ${
                              (getY1(connection) + getY2(connection)) / 2
                          })`
                        : undefined
                "
            >
                {{ connection.cost }}
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
                :scale="house.scale"
            />
        </template>

        <!-- Bremen entry-cost number, on top so it stays readable over houses -->
        <template v-for="city in cities">
            <g
                v-if="city.connectionCost != null && city.slotCosts && city.slotCosts.length >= 2"
                :key="city.name + '_cc'"
            >
                <circle
                    :cx="city.x"
                    :cy="city.y + 15"
                    r="11"
                    fill="goldenrod"
                    stroke="darkgoldenrod"
                    stroke-width="2"
                />
                <circle :cx="city.x" :cy="city.y + 15" r="7.5" fill="gray" stroke="darkgoldenrod" stroke-width="1" />
                <text
                    :x="city.x"
                    :y="city.y + 15"
                    font-size="11"
                    font-weight="bold"
                    text-anchor="middle"
                    dominant-baseline="central"
                    fill="black"
                    :transform="mapRotation ? `rotate(${-mapRotation}, ${city.x}, ${city.y + 15})` : undefined"
                >
                    {{ city.connectionCost }}
                </text>
            </g>
        </template>

        <template v-for="city in cities">
            <!-- [10,15] city: X at bottom-right -->
            <template v-if="city.slotCosts && city.slotCosts.length === 2 && city.slotCosts[0] === 10">
                <line
                    :key="city.name + '_x1'"
                    :x1="city.x + 10"
                    :y1="city.y + 10"
                    :x2="city.x + 19"
                    :y2="city.y + 19"
                    stroke="black"
                    stroke-width="3"
                    stroke-linecap="round"
                />
                <line
                    :key="city.name + '_x2'"
                    :x1="city.x + 19"
                    :y1="city.y + 10"
                    :x2="city.x + 10"
                    :y2="city.y + 19"
                    stroke="black"
                    stroke-width="3"
                    stroke-linecap="round"
                />
            </template>
            <!-- [10,10,20] city: "10" label at bottom-left (two 10-Elektro slots) -->
            <text
                v-if="
                    city.slotCosts &&
                    city.slotCosts.length === 3 &&
                    city.slotCosts[0] === 10 &&
                    city.slotCosts[1] === 10
                "
                :key="city.name + '_10label'"
                :x="city.x - 20"
                :y="city.y + 19"
                font-size="17"
                font-weight="bold"
                fill="black"
                text-anchor="middle"
                :transform="mapRotation ? `rotate(${-mapRotation}, ${city.x - 20}, ${city.y + 19})` : undefined"
                >10</text
            >
            <!-- [15,20] city: X at top-middle -->
            <template v-if="city.slotCosts && city.slotCosts.length === 2 && city.slotCosts[0] === 15">
                <line
                    :key="city.name + '_x1'"
                    :x1="city.x - 5"
                    :y1="city.y - 21"
                    :x2="city.x + 5"
                    :y2="city.y - 11"
                    stroke="black"
                    stroke-width="3"
                    stroke-linecap="round"
                />
                <line
                    :key="city.name + '_x2'"
                    :x1="city.x + 5"
                    :y1="city.y - 21"
                    :x2="city.x - 5"
                    :y2="city.y - 11"
                    stroke="black"
                    stroke-width="3"
                    stroke-linecap="round"
                />
            </template>
        </template>

        <template v-if="!preferences.disableHelp">
            <template v-for="city in cities">
                <circle
                    v-if="canBuild(city)"
                    :key="city.name + '_circleHelp'"
                    :class="[{ canClick: canBuild(city) }]"
                    r="18"
                    :cx="city.x"
                    :cy="city.y"
                    fill="none"
                    stroke="blue"
                    stroke-width="4px"
                />
            </template>
        </template>

        <!-- chooseRegions draft: outline every city in a pickable region so the
             current player can see and click the regions they may draft. Shown
             regardless of the help preference since the draft can't proceed
             without it. -->
        <template v-for="city in cities">
            <circle
                v-if="canPickRegion(city)"
                :key="city.name + '_pickRegion'"
                class="canClick"
                r="18"
                :cx="city.x"
                :cy="city.y"
                fill="none"
                stroke="gold"
                stroke-width="5px"
                @click="onCityClick(city)"
            />
        </template>

        <!-- Regions where nuclear plants are banned: a nuclear-plant tile under a red
             prohibition sign (ring + diagonal bar), matching the marker printed on
             the physical board. -->
        <g
            v-for="marker in noUraniumMarkers"
            :key="'noUranium_' + marker.region"
            :transform="`translate(${marker.x}, ${marker.y})`"
        >
            <!-- nuclear plant tile: dark card with the red uranium barrel glyph -->
            <rect x="-15" y="-11" width="30" height="22" rx="3" fill="#4a4a4a" stroke="black" stroke-width="1.5" />
            <g transform="translate(-9, -7) scale(1.2)">
                <path d="M1,2 l4,-2 l6,0 l4,2 l0,11 l-4,2 l-6,0 l-4,-2Z" fill="#ef3b3b" />
            </g>
            <!-- prohibition sign over it, tinted with the region's own colour -->
            <circle cx="0" cy="0" r="20" fill="none" :stroke="marker.region" stroke-width="4.5" />
            <line
                x1="-14.1"
                y1="-14.1"
                x2="14.1"
                y2="14.1"
                :stroke="marker.region"
                stroke-width="4.5"
                stroke-linecap="round"
            />
        </g>
    </g>
</template>

<script lang="ts">
import type { GameState } from 'powergrid-engine';
import { Vue, Component, Prop, Inject } from 'vue-property-decorator';
import { House } from '../pieces';
import { Piece, Preferences } from '../../types/ui-data';
import { City, Connection, Polygon } from 'powergrid-engine/src/maps';

@Component({
    components: {
        House,
    },
})
export default class Map extends Vue {
    @Prop() polygons?: Polygon[];
    @Prop() cities?: City[];
    @Prop() connections?: Connection[];
    @Prop() playerColors?: string[];
    @Prop() buildableCities?: string[];
    // Manhattan: spaces blocked for this player count — transitable but never buildable.
    @Prop() blockedCities?: string[];
    // chooseRegions draft: region names the current player may pick this turn.
    @Prop() pickableRegions?: string[];
    // Regions where nuclear plants are banned; each gets a struck-through marker.
    @Prop() noUraniumRegions?: string[];
    @Prop() devBackdrop?: { src: string; width: number; height: number; opacity?: number };
    @Prop({ default: 0 }) mapRotation!: number;

    @Inject() preferences!: Preferences;

    houses: Piece[] = [];

    createPieces(gameState: GameState) {
        this.houses = [];
        gameState.players.forEach((player, pi) => {
            player.cities.forEach((cityPiece) => {
                const city = gameState.map.cities.find((city) => city.name == cityPiece.name)!;
                let offsetX, offsetY;
                let pieceScale: number | undefined;
                const isNodeWeighted = city.connectionCost != null;
                // Manhattan = a node-weighted map with exactly one house per space.
                const isManhattan = isNodeWeighted && city.slotCosts?.length === 1;
                const is1520 = city.slotCosts?.length === 2 && city.slotCosts[0] === 15;
                if (isManhattan) {
                    // One house per space, enlarged and centered so the house silhouette
                    // slightly overflows the (smaller) price tile and covers it — no white
                    // corners showing. The House shape's bbox center is ~(199, 230) in its
                    // own units, so at scale S it centers on the space when offset -199S/-230S.
                    pieceScale = 0.085;
                    offsetX = -199 * pieceScale;
                    offsetY = -230 * pieceScale;
                } else if (isNodeWeighted) {
                    // Bremen tiles: 8 top, 14 left, 20 right — matches the board layout.
                    // The House piece is anchored top-left (~14×16 after its scale), so
                    // offset by half its size to center it on the slot.
                    const slot = this.nodeSlotPos(cityPiece.position);
                    offsetX = slot.dx - 7;
                    offsetY = slot.dy - 8;
                } else if (is1520) {
                    // [15,20] city: slot 0 (cost 15) → bottom-left, slot 1 (cost 20) → bottom-right
                    if (cityPiece.position == 0) {
                        offsetX = -15;
                        offsetY = -4;
                    } else {
                        offsetX = 1;
                        offsetY = -4;
                    }
                } else if (cityPiece.position == 0) {
                    offsetX = -6;
                    offsetY = -18;
                } else if (cityPiece.position == 1) {
                    offsetX = -15;
                    offsetY = -4;
                } else {
                    offsetX = 1;
                    offsetY = -4;
                }

                this.houses.push({
                    id: pi + '_' + cityPiece.name,
                    x: city.x + offsetX,
                    y: city.y + offsetY,
                    color: this.playerColors![pi],
                    owner: pi,
                    scale: pieceScale,
                });
            });
        });
    }

    getX1(connection) {
        const city = this.cities!.find((city) => city.name == connection.nodes[0])!;
        return city.x;
    }

    getY1(connection) {
        const city = this.cities!.find((city) => city.name == connection.nodes[0])!;
        return city.y;
    }

    getX2(connection) {
        const city = this.cities!.find((city) => city.name == connection.nodes[1])!;
        return city.x;
    }

    getY2(connection) {
        const city = this.cities!.find((city) => city.name == connection.nodes[1])!;
        return city.y;
    }

    nodeSlotPos(i: number) {
        // House slots laid out like the printed board: 0 = 8 (top), 1 = 14 (left), 2 = 20 (right).
        if (i === 0) return { dx: 0, dy: -15 };
        if (i === 1) return { dx: -15, dy: 0 };
        return { dx: 15, dy: 0 };
    }

    // One "no nuclear" marker per banned region. Placed at the most open spot
    // inside the region — the point (within the region's own area) that is farthest
    // from every city and every connection cost-label — so the marker never covers a
    // city node or a connection cost. Uses the already-adjusted city coordinates, so
    // it needs no knowledge of the map's adjustRatio.
    get noUraniumMarkers(): { region: string; x: number; y: number }[] {
        if (!this.noUraniumRegions || !this.cities || this.cities.length === 0) return [];
        const cities = this.cities;

        // Obstacles the marker must avoid: city centres and connection cost labels
        // (drawn at each connection's midpoint).
        const obstacles = cities.map((c) => ({ x: c.x, y: c.y }));
        for (const con of this.connections ?? []) {
            if (!con.cost || con.cost <= 0) continue;
            const a = cities.find((c) => c.name === con.nodes[0]);
            const b = cities.find((c) => c.name === con.nodes[1]);
            if (a && b) obstacles.push({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });
        }

        const nearestDist = (x: number, y: number, pts: { x: number; y: number }[]) => {
            let min = Infinity;
            for (const p of pts) {
                const d = Math.hypot(p.x - x, p.y - y);
                if (d < min) min = d;
            }
            return min;
        };

        const markers: { region: string; x: number; y: number }[] = [];
        for (const region of this.noUraniumRegions) {
            const regionCities = cities.filter((c) => c.region === region);
            if (regionCities.length === 0) continue;

            const xs = regionCities.map((c) => c.x);
            const ys = regionCities.map((c) => c.y);
            const centroid = { x: xs.reduce((s, v) => s + v, 0) / xs.length, y: ys.reduce((s, v) => s + v, 0) / ys.length };

            // Scan a grid over the region's bounding box for points that fall inside
            // this region (nearest city belongs to it). Among those with enough
            // clearance to not cover an obstacle, prefer the one closest to the
            // region centre so the marker stays central rather than drifting to an
            // empty edge. Fall back to the most open point if none clear the bar.
            const MIN_CLEARANCE = 44; // marker radius (~22) + obstacle radius (~20) + gap
            let central: { x: number; y: number; distToCentroid: number } | undefined;
            let openest: { x: number; y: number; clearance: number } | undefined;
            const step = 10;
            for (let x = Math.min(...xs); x <= Math.max(...xs); x += step) {
                for (let y = Math.min(...ys); y <= Math.max(...ys); y += step) {
                    let nearestCity = regionCities[0];
                    let nd = Infinity;
                    for (const c of cities) {
                        const d = Math.hypot(c.x - x, c.y - y);
                        if (d < nd) {
                            nd = d;
                            nearestCity = c;
                        }
                    }
                    if (nearestCity.region !== region) continue;

                    const clearance = nearestDist(x, y, obstacles);
                    if (!openest || clearance > openest.clearance) openest = { x, y, clearance };

                    if (clearance >= MIN_CLEARANCE) {
                        const distToCentroid = Math.hypot(x - centroid.x, y - centroid.y);
                        if (!central || distToCentroid < central.distToCentroid) central = { x, y, distToCentroid };
                    }
                }
            }

            const chosen = central ?? openest;
            markers.push({ region, x: chosen ? chosen.x : centroid.x, y: chosen ? chosen.y : centroid.y });
        }
        return markers;
    }

    canBuild(city: City) {
        return !!this.buildableCities!.find((cityName) => cityName == city.name);
    }

    isBlocked(city: City) {
        return !!this.blockedCities && this.blockedCities.includes(city.name);
    }

    build(city: City) {
        this.$emit('build', city);
    }

    canPickRegion(city: City) {
        return !!this.pickableRegions && this.pickableRegions.includes(city.region);
    }

    pickRegion(city: City) {
        this.$emit('pickRegion', city.region);
    }

    // During the region draft a city click picks its region; otherwise it builds.
    onCityClick(city: City) {
        if (this.canBuild(city)) {
            this.build(city);
        } else if (this.canPickRegion(city)) {
            this.pickRegion(city);
        }
    }

    onPickCoord(e: MouseEvent) {
        if (!this.devBackdrop) return;
        const g = e.currentTarget as SVGGElement;
        const ctm = g.getScreenCTM();
        if (!ctm) return;
        const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(ctm.inverse());
        // eslint-disable-next-line no-console
        console.log(`{ name: Cities.TODO, region: Regions.TODO, x: ${Math.round(pt.x)}, y: ${Math.round(pt.y)} },`);
    }
}
</script>
