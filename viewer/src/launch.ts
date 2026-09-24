import { installPlayerCards, createBoardThumbnail } from './host-presentation';
import { createViewer } from '@boardgamers/protocol/viewer';
import { EventEmitter } from 'events';
import type { GameState, Move } from 'powergrid-engine';
import type { PremoveCommand } from 'powergrid-engine/src/premoves';
import Vue from 'vue';
import Game from './components/Game.vue';
import { mountGameChat } from './game-chat';
import { installActionSounds } from './sounds';
import type { Preferences } from './types/ui-data';
import { shouldAdoptLogState } from './util/turn-buffer';

let dispose: (() => void) | undefined;

export function destroyViewer() {
    dispose?.();
    dispose = undefined;
}

function launch(selector: string) {
    const target = document.querySelector(selector);
    if (!target) throw new Error(`Viewer mount point not found: ${selector}`);
    dispose?.();
    const mountPoint = document.createElement('div');
    target.append(mountPoint);
    let params: {
        state: null | GameState;
        player?: number;
        emitter: EventEmitter;
        preferences: Preferences;
        avatars: string[];
    } = {
        state: null,
        emitter: new EventEmitter(),
        // Observable so preference changes update the UI immediately: Game receives
        // this object as a prop, and Vue 2 does not deep-observe prop values coming
        // from a non-reactive parent — plain-object mutations (the in-game sound/help
        // toggles, platform preference pushes) would only paint on the next re-render.
        preferences: Vue.observable({
            sound: true,
            disableHelp: false,
            adjustPlayerOrder: false,
            undoWholeTurn: true,
            fitToScreen: true,
            stackOnPortrait: true,
            portraitResourceTrack: false,
        }),
        avatars: [],
    };

    const app = new Vue({
        render: (h) => h(Game, { props: params }, []),
    }).$mount(mountPoint);

    const thumbnail = createBoardThumbnail(app.$el);
    let replaying = false;
    const viewer = createViewer<GameState, Move[] | PremoveCommand>({
        async onThumbnail(size) {
            await app.$nextTick();
            return thumbnail.render(app.$el.querySelector('[data-tutorial="map"]'), size, '#e7e6df');
        },
        async onState(data) {
            params.state = data;
            app.$forceUpdate();
            await app.$nextTick();
        },
        onPlayer(data) {
            params.player = data.index;
            app.$forceUpdate();
        },
        onPreferences(data) {
            Object.assign(params.preferences, data);
            app.$forceUpdate();
        },
        onAvatars(data) {
            params.avatars = data;
            app.$forceUpdate();
        },
        onUpdate() {
            if (!replaying) viewer.fetchState();
        },
        async onLog(logData) {
            if (replaying) return;
            const data = logData.data as { state?: GameState } | undefined;
            // Only tentative move responses may replace the local turn buffer.
            if (shouldAdoptLogState(data?.state)) {
                params.state = data!.state!;
                app.$forceUpdate();
                await app.$nextTick();
            } else viewer.fetchState();
        },
        onReplayStart() {
            replaying = true;
            params.emitter.emit('replayStart');
        },
        onReplayTo(index) {
            params.emitter.emit('replayTo', index);
        },
        onReplayEnd() {
            params.emitter.emit('replayEnd');
            replaying = false;
            viewer.fetchState();
        },
    });
    const item = viewer.emitter;
    params.emitter.on('move', (moves: Move[]) => viewer.move(moves));
    params.emitter.on('premoves', (command: PremoveCommand) => viewer.move(command));
    params.emitter.on('fetchState', () => viewer.fetchState());
    params.emitter.on('addLog', (data: string[]) => viewer.addLog(data));
    params.emitter.on('replaceLog', (data: string[]) => viewer.replaceLog(data));
    params.emitter.on('replay:info', (info) => viewer.setReplayInfo(info));
    params.emitter.on('update:preference', ({ name, value }) => viewer.updatePreference(name, value));
    installActionSounds(item);
    const removeCards = installPlayerCards(app.$el, viewer);
    const removeChat = mountGameChat(item, app.$el);
    app.$once('hook:beforeDestroy', () => {
        removeCards();
        thumbnail.destroy();
        removeChat();
        viewer.destroy();
        params.emitter.removeAllListeners();
    });
    dispose = () => {
        app.$destroy();
        target.replaceChildren();
    };
    return item;
}

export default launch;
