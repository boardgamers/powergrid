<template>
    <details class="inline-game-log" open>
        <summary>Journal</summary>
        <div ref="feed" class="journal-feed" @scroll="onScroll">
            <div v-for="(entry, index) in illustratedEntries" :key="index" class="journal-entry" translate="no">
                <template v-for="(part, i) in entry">
                    <svg
                        v-if="part.plant"
                        :key="i"
                        class="journal-plant"
                        viewBox="-2 -2 64 44"
                        role="img"
                        :aria-label="plantLabel(part.plant)"
                    >
                        <title>{{ plantLabel(part.plant) }}</title>
                        <Card :powerPlant="part.plant" />
                    </svg>
                    <span v-else :key="i" v-html="part.html" />
                </template>
            </div>
            <div v-if="!entries.length">No actions yet.</div>
        </div>
    </details>
</template>
<script lang="ts">
import { Component, Prop, Vue, Watch } from 'vue-property-decorator';
import Card from './pieces/Card.vue';
import { getPowerPlant } from 'powergrid-engine/src/engine';
import { translateText } from '../localization';
import { localizeJournal } from '../localization/journal';
import type { PowerPlant } from 'powergrid-engine/src/gamestate';
@Component({ components: { Card } })
export default class InlineLog extends Vue {
    @Prop({ default: () => [] }) entries!: string[];
    @Prop({ default: '' }) mapName!: string;
    follow = true;
    private feedObserver?: ResizeObserver;
    locale = 'en';
    private localeObserver?: MutationObserver;
    get illustratedEntries() {
        return this.entries.map((entry) => localizeJournal(
            entry,
            (text: string) => translateText(text, this.locale),
            (number: number) => getPowerPlant(number, this.mapName)
        ));
    }
    plantLabel(plant: PowerPlant) {
        return translateText(`Power plant ${plant.number}: ${plant.cost ? `${plant.cost} ${plant.type}` : 'no fuel'} → ${
            plant.citiesPowered
        } cities`, this.locale);
    }
    mounted() {
        const updateLocale = () => {
            this.locale = this.$el.closest('[lang]')?.getAttribute('lang') || 'en';
        };
        updateLocale();
        this.localeObserver = new MutationObserver(updateLocale);
        let ancestor: Element | null = this.$el;
        while (ancestor) {
            this.localeObserver.observe(ancestor, { attributes: true, attributeFilter: ['lang'] });
            ancestor = ancestor.parentElement;
        }
        this.feedObserver = new ResizeObserver(() => {
            if (this.follow) this.scrollToLatest();
        });
        this.feedObserver.observe(this.$refs.feed as HTMLElement);
        this.scrollToLatest();
    }
    beforeDestroy() {
        this.localeObserver?.disconnect();
        this.feedObserver?.disconnect();
    }
    @Watch('entries') changed() {
        if (this.follow) {
            this.$nextTick(this.scrollToLatest);
        }
    }
    scrollToLatest() {
        const feed = this.$refs.feed as HTMLElement;
        if (feed?.clientHeight) {
            feed.scrollTop = feed.scrollHeight;
        }
    }
    onScroll() {
        const feed = this.$refs.feed as HTMLElement;
        if (feed.clientHeight) this.follow = feed.scrollHeight - feed.scrollTop - feed.clientHeight < 32;
    }
}
</script>
<style scoped>
.inline-game-log {
    box-sizing: border-box;
    width: 100%;
    padding: 10px 14px;
    border: 1px solid #a2aa82;
    border-radius: 3px;
    background: #f3f0dc;
    color: #263521;
    font: 14px Arial, sans-serif;
}
summary {
    cursor: pointer;
    font-weight: 600;
}
.journal-feed {
    max-height: 220px;
    overflow: auto;
    overscroll-behavior: auto;
    margin-top: 8px;
}
.journal-plant {
    width: 76px;
    height: 52px;
    vertical-align: middle;
    margin: 1px 4px;
    overflow: visible;
}
.journal-entry {
    padding: 5px 0;
    border-bottom: 1px solid #75818d33;
}
</style>
