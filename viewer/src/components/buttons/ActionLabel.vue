<template>
    <text
        ref="label"
        data-action-label
        :x="width / 2"
        :y="height / 2"
        text-anchor="middle"
        dominant-baseline="central"
        :font-size="fontSize"
        fill="black"
        aria-hidden="true"
        pointer-events="none"
        >{{ text }}</text
    >
</template>
<script lang="ts">
import { Vue, Component, Prop, Watch } from 'vue-property-decorator';

/** Keep the complete source in one text node for the DOM localization adapter.
 * Fit the translated glyphs, never truncate the action or squeeze only its width. */
@Component
export default class ActionLabel extends Vue {
    @Prop() text!: string;
    @Prop() width!: number;
    @Prop() height!: number;
    fontSize = 13;
    private textObserver: MutationObserver | null = null;
    private sizeObserver: ResizeObserver | null = null;
    private disposed = false;

    @Watch('text')
    @Watch('width')
    @Watch('height')
    fit() {
        if (this.disposed) return;
        const label = this.$refs.label as SVGTextElement | undefined;
        if (!label || typeof label.getComputedTextLength !== 'function') return;
        const length = label.getComputedTextLength();
        const height = label.getBBox().height;
        if (!length || !height) return; // Hidden iframe: ResizeObserver retries on reveal.
        const current = Number(label.getAttribute('font-size'));
        this.fontSize =
            Math.round(
                Math.min(13, (current * (this.width - 16)) / length, (current * (this.height - 8)) / height) * 100
            ) / 100;
    }

    mounted() {
        const label = this.$refs.label as SVGTextElement;
        // Locale switches change the actual DOM, without changing the English prop.
        if (typeof MutationObserver !== 'undefined') {
            this.textObserver = new MutationObserver(() => this.fit());
            this.textObserver.observe(label, { childList: true, characterData: true, subtree: true });
        }
        if (typeof ResizeObserver !== 'undefined') {
            this.sizeObserver = new ResizeObserver(() => this.fit());
            this.sizeObserver.observe(label);
        }
        this.$nextTick(this.fit);
        document.fonts?.ready.then(() => this.fit());
    }

    beforeDestroy() {
        this.disposed = true;
        this.textObserver?.disconnect();
        this.sizeObserver?.disconnect();
    }
}
</script>
