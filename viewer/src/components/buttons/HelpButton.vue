<template>
    <g class="button enabled" @click="$emit('click')">
        <circle cx="15" cy="15" r="15" fill="gainsboro" stroke="black" stroke-width="2px" />
        <image x="5" y="5" width="20" height="20" href="../../icons/help.svg" />
        <line v-if="!isOn" x1="5" y1="25" x2="25" y2="5" stroke="black" stroke-width="3px" stroke-linecap="round" />
        <title v-if="isOn">Help off</title>
        <title v-else>Help on</title>
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component
export default class HelpButton extends Vue {
    @Prop()
    isOn?: boolean;
}
</script>
