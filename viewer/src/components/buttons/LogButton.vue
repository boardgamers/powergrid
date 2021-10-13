<template>
    <g class="button enabled" @click="$emit('click')">
        <rect width="80" height="26" fill="gainsboro" stroke="black" rx="2" />
        <image x="11" y="5" width="16" height="16" href="../../icons/log.svg" />
        <text text-anchor="middle" fill="black" x="47" y="13">Log</text>
        <title>Show log</title>
    </g>
</template>
<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';

@Component
export default class LogButton extends Vue {
}
</script>
