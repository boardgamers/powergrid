<template>
    <g v-if="geography && bounds && appearance !== 'none'" data-geography-map pointer-events="none" aria-hidden="true">
        <metadata>
            Geographic backdrop adapted from Natural Earth (public domain), GeoNames (https://www.geonames.org/, CC BY
            4.0, https://creativecommons.org/licenses/by/4.0/) and NYC Open Data
            (https://data.cityofnewyork.us/d/gthc-hcne). Shapes are fitted to the schematic game network; see
            viewer/scripts/geography/README.md.
        </metadata>
        <defs>
            <clipPath :id="clipId" clipPathUnits="userSpaceOnUse">
                <rect :x="bounds.x" :y="bounds.y" :width="bounds.width" :height="bounds.height" />
            </clipPath>
        </defs>
        <g data-geography-content :clip-path="fullBoard ? undefined : `url(#${clipId})`">
            <rect
                v-if="appearance === 'terrain'"
                :x="bounds.x"
                :y="bounds.y"
                :width="bounds.width"
                :height="bounds.height"
                fill="#96bcc5"
            />
            <g :transform="`scale(${ratio[0]}, ${ratio[1]})`" fill-rule="evenodd" stroke-linejoin="round">
                <path
                    v-for="(path, i) in appearance === 'terrain' ? geography.context : []"
                    :key="'context' + i"
                    :d="path"
                    fill="#91b374"
                />
                <path
                    v-for="(path, i) in geography.land"
                    :key="'land' + i"
                    :d="path"
                    :fill="appearance === 'line' ? 'none' : appearance === 'terrain' ? '#bfd58c' : '#dce8aa'"
                    :fill-opacity="appearance === 'wash' ? 0.48 : 1"
                    stroke="#526b39"
                    stroke-opacity="0.65"
                    :stroke-width="1.6 / Math.max(...ratio)"
                />
            </g>
        </g>
    </g>
</template>

<script lang="ts">
import { Vue, Component, Prop, Watch } from 'vue-property-decorator';
import type { GameMap } from 'powergrid-engine/src/maps';
import { geographyForMap, loadGeography, GeographyStyle, MapBounds } from '../../geography';
let nextId = 0;

@Component
export default class GeographicBackground extends Vue {
    @Prop() map?: GameMap;
    @Prop() bounds?: MapBounds;
    @Prop({ default: false }) fullBoard!: boolean;
    @Prop({ default: 'terrain' }) appearance!: GeographyStyle;
    clipId = `powergrid-geography-${++nextId}`;
    ready = false;
    @Watch('map.name', { immediate: true })
    async loadMap() {
        this.ready = false;
        const name = this.map?.name;
        if (!name) return;
        try {
            await loadGeography(name);
            if (this.map?.name === name) this.ready = true;
        } catch (error) { console.warn('Geographic background could not load', error); }
    }
    get geography() { return this.ready ? geographyForMap(this.map) : undefined; }
    @Watch('geography', { immediate: true })
    onGeographyChanged() { this.$emit('availability', !!this.geography); }
    get ratio() { return this.map?.adjustRatio || [1, 1]; }
}
</script>
