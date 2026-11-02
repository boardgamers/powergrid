<template>
    <!-- Each piece already defines its board scale; scale that common 20-unit
         footprint, rather than overriding differently authored SVG coordinates. -->
    <g :transform="`scale(${size / 20})`" class="resource-token" :data-resource="resource">
        <component :is="icon" :pieceId="-1" :targetState="{ x: 0, y: 0 }" :canClick="false" :transparent="false" />
    </g>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';
import Coal from '../pieces/Coal.vue';
import Oil from '../pieces/Oil.vue';
import Garbage from '../pieces/Garbage.vue';
import Uranium from '../pieces/Uranium.vue';
@Component({ components: { Coal, Oil, Garbage, Uranium } })
export default class ResourceToken extends Vue {
    @Prop({ required: true }) resource!: string;
    @Prop({ default: 32 }) size!: number;
    get icon(): string { return this.resource[0].toUpperCase() + this.resource.slice(1); }
}
</script>
