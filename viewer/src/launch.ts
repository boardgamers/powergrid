import { EventEmitter } from 'events';
import type { GameState, Move } from 'powergrid-engine';
import Vue from 'vue';
import Game from './components/Game.vue';
import type { Preferences } from './types/ui-data';

function launch(selector: string) {
    let params: {
        state: null | GameState;
        player?: number;
        emitter: EventEmitter;
        preferences: Preferences;
        avatars: string[];
    } = {
        state: null,
        emitter: new EventEmitter(),
        preferences: {
            sound: true,
            disableHelp: false,
            adjustPlayerOrder: false,
            undoWholeTurn: true,
        },
        avatars: [],
    };

    const app = new Vue({
        render: (h) => h(Game, { props: params }, []),
    }).$mount(selector);

    const item: EventEmitter = new EventEmitter();
    let replaying = false;

    params.emitter.on('move', (move: Move) => item.emit('move', move));
    params.emitter.on('fetchState', () => item.emit('fetchState'));
    params.emitter.on('addLog', (data: string[]) => item.emit('addLog', data));
    params.emitter.on('replaceLog', (data: string[]) => item.emit('replaceLog', data));
    params.emitter.on('replay:info', (info: { start: number; current: number; end: number }) =>
        item.emit('replay:info', info)
    );
    params.emitter.on('update:preference', (data: { name: string; value: any }) =>
        item.emit('update:preference', data)
    );
    item.addListener('avatars', (data) => {
        params.avatars = data;
        app.$forceUpdate();
    });

    item.addListener('state', (data) => {
        params.state = data;
        app.$forceUpdate();
        app.$nextTick().then(() => item.emit('ready'));
    });
    item.addListener('state:updated', () => item.emit('fetchState'));
    item.addListener('player', (data) => {
        params.player = data.index;
        app.$forceUpdate();
    });
    item.addListener('preferences', (data) => {
        params.preferences = { ...params.preferences, ...data };
        app.$forceUpdate();
    });
    item.addListener('gamelog', (_) => {
        if (replaying) {
            return;
        }

        item.emit('fetchState');
    });

    item.addListener('replay:start', () => {
        params.emitter.emit('replayStart');
        replaying = true;
    });
    item.addListener('replay:to', (info) => {
        params.emitter.emit('replayTo', info);
    });
    item.addListener('replay:end', () => {
        params.emitter.emit('replayEnd');
        replaying = false;
        item.emit('fetchState');
    });

    return item;
}

export default launch;
