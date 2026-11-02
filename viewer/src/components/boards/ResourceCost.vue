<template>
    <g class="resource-cost">
        <rect
            width="78"
            height="46"
            rx="10"
            :fill="muted ? '#e3e8cf' : '#365343'"
            :stroke="muted ? '#819578' : '#294432'"
            stroke-width="2"
        />
        <template v-if="amount != null">
            <text
                x="15"
                y="25"
                text-anchor="middle"
                dominant-baseline="middle"
                font-size="27"
                font-weight="600"
                :fill="muted ? '#365343' : '#e9ddb4'"
                >$</text
            >
            <text
                x="47"
                y="25"
                text-anchor="middle"
                dominant-baseline="middle"
                font-size="32"
                font-weight="700"
                :fill="muted ? '#365343' : '#fff3cf'"
                >{{ amount }}</text
            >
        </template>
        <text
            v-else
            x="39"
            y="25"
            text-anchor="middle"
            dominant-baseline="middle"
            font-size="28"
            :fill="muted ? '#365343' : '#fff3cf'"
            >—</text
        >
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
@Component
export default class ResourceCost extends Vue {
    @Prop() amount!: number | null;
    @Prop({ default: false }) muted!: boolean;
}
</script>
