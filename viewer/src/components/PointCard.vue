<template>
    <g class="point-card" @click="turned = !turned">
        <g v-if="turned">
            <rect width="100" height="160" fill="dimgray" stroke="white" stroke-width="2" rx="2" />
        </g>
        <g v-else>
            <rect width="100" height="160" fill="silver" stroke="white" stroke-width="2" rx="2" />
            <rect
                x="20"
                y="15"
                width="20"
                height="10"
                :fill="pointCard.containerValues[0].containerColor"
                stroke="black"
            />
            <text x="70" y="20" text-anchor="middle">10</text>
            <rect
                x="20"
                y="45"
                width="20"
                height="10"
                :fill="pointCard.containerValues[1].containerColor"
                stroke="black"
            />
            <text x="70" y="50" text-anchor="middle">5/10</text>
            <rect
                x="20"
                y="75"
                width="20"
                height="10"
                :fill="pointCard.containerValues[2].containerColor"
                stroke="black"
            />
            <text x="70" y="80" text-anchor="middle">6</text>
            <rect
                x="20"
                y="105"
                width="20"
                height="10"
                :fill="pointCard.containerValues[3].containerColor"
                stroke="black"
            />
            <text x="70" y="110" text-anchor="middle">4</text>
            <rect
                x="20"
                y="135"
                width="20"
                height="10"
                :fill="pointCard.containerValues[4].containerColor"
                stroke="black"
            />
            <text x="70" y="140" text-anchor="middle">2</text>
        </g>
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import type { PointCard as PointCardInfo } from 'container-engine'

@Component
export default class PointCard extends Vue {
    @Prop()
    pointCard?: PointCardInfo;

    turned = false;
}
</script>
<style lang="scss">
.point-card {
    cursor: pointer;
}
</style>
