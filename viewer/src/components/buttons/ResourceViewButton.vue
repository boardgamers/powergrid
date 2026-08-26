<template>
    <!--
        Which resource display the portrait layout shows. A labelled either/or rather
        than an icon: this changes what the whole row below it *is*, and no picture of
        "boxes" or "a track" is recognisable before you tap it.

        Authored 620x72 so that, held to the same 0.94 width budget as the box market
        underneath, the two line up edge to edge and each half clears the 44px tap
        guideline on a 414px-wide phone.
    -->
    <g class="resourceView">
        <g class="button enabled" @click="$emit('select', false)">
            <rect
                x="0"
                y="0"
                width="306"
                height="72"
                rx="6"
                :fill="showTrack ? 'gainsboro' : '#333'"
                stroke="black"
                stroke-width="3"
            />
            <text
                x="153"
                y="47"
                text-anchor="middle"
                font-weight="700"
                :fill="showTrack ? 'black' : 'white'"
                style="font-size: 30px"
            >
                Buy boxes
            </text>
            <title>One box per buyable source: the price you pay, and the whole box is the tap target</title>
        </g>
        <g class="button enabled" @click="$emit('select', true)">
            <rect
                x="314"
                y="0"
                width="306"
                height="72"
                rx="6"
                :fill="showTrack ? '#333' : 'gainsboro'"
                stroke="black"
                stroke-width="3"
            />
            <text
                x="467"
                y="47"
                text-anchor="middle"
                font-weight="700"
                :fill="showTrack ? 'white' : 'black'"
                style="font-size: 30px"
            >
                Price track
            </text>
            <title>The printed market board, so the whole price track is visible at once</title>
        </g>
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component
export default class ResourceViewButton extends Vue {
    @Prop()
    showTrack?: boolean;
}
</script>
