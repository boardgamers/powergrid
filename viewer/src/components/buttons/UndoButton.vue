<template>
    <g :class="['button', { enabled }]" @click="enabled && $emit('click')">
        <rect width="80" height="26" fill="gainsboro" stroke="black" rx="2" />
        <image x="11" y="4" width="16" height="16" href="../../icons/undo.svg" />
        <text text-anchor="middle" fill="black" x="47" y="13">Undo</text>
        <title>Undo last move</title>
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component
export default class UndoButton extends Vue {
    @Prop()
    enabled!: boolean;
}
</script>
