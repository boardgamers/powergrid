<template>
    <g :class="['button', { enabled, highlightButton }]" @click="enabled && $emit('click')">
        <rect width="80" height="26" fill="gainsboro" stroke="black" rx="2" />
        <image x="15" y="8" width="10" height="10" href="../../icons/pass.svg" />
        <text text-anchor="middle" fill="black" x="47" y="13">{{ text }}</text>
        <title>Pass turn</title>
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop, Inject } from 'vue-property-decorator';

@Component
export default class PassButton extends Vue {
    @Prop() enabled!: boolean;
    @Prop() highlightButton!: boolean;
    @Prop() text!: string;
}
</script>
