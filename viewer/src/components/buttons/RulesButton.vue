<template>
    <g class="button enabled" @click="$emit('click')">
        <circle cx="15" cy="15" r="15" fill="gainsboro" stroke="black" stroke-width="2px" />
        <image x="5" y="5" width="20" height="20" href="../../icons/rules.svg" />
        <title>Rules</title>
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component
export default class RulesButton extends Vue {
}
</script>
