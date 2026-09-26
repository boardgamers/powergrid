import { createTutorial, TutorialMount, TutorialSnapshot } from '@boardgamers/protocol/tutorial';
import { mountTutorialGuide } from '@boardgamers/protocol/tutorial/dom';
import { EventEmitter } from 'events';
import { GameState, stripSecret } from 'powergrid-engine';
import Vue from 'vue';
import Game from '../components/Game.vue';
import { Action, lessons, LessonState } from './lessons';
import './tutorial.css';

export const mountTutorial: TutorialMount = async (target, { chapter, onProgress, nextChapter }) => {
    const lesson = lessons.find((entry) => entry.id === chapter);
    if (!lesson) throw Error('Unknown Powergrid chapter');
    target.className = 'powergrid-tutorial';
    const guide = document.createElement('section');
    const controls = document.createElement('div');
    controls.className = 'tutorial-answers';
    controls.setAttribute('aria-label', 'Lesson answers');
    const summary = document.createElement('div');
    summary.className = 'tutorial-summary';
    const board = document.createElement('div');
    board.className = 'tutorial-board';
    target.append(guide, controls, summary, board);
    const emitter = new EventEmitter();
    const params = {
        state: null as GameState | null,
        player: 0,
        avatars: ['Y', 'A', 'L'].map(
            (initial) =>
                'data:image/svg+xml,' +
                encodeURIComponent(
                    `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48"><circle cx="24" cy="24" r="23" fill="#233745"/><text x="24" y="31" text-anchor="middle" font-family="sans-serif" font-size="24" fill="white">${initial}</text></svg>`
                )
        ),
        tutorialCity: undefined as string | undefined,
        emitter,
        preferences: Vue.observable({
            sound: false,
            colorBlind: false,
            disableHelp: false,
            adjustPlayerOrder: false,
            undoWholeTurn: true,
            fitToScreen: true,
            stackOnPortrait: true,
            portraitResourceTrack: false,
        }),
        interactionDisabled: false,
        tutorialMove: (move) => {
            void play({ kind: 'move', move });
        },
    };
    const app = new Vue({ render: (h) => h(Game, { props: params }) }).$mount(
        board.appendChild(document.createElement('div'))
    );
    let destroyed = false;
    let animate = false;
    let timer: number | undefined;
    let finishFrame: (() => void) | undefined;
    let latest: TutorialSnapshot<LessonState>;
    let previous: LessonState | undefined;
    async function present(game: GameState) {
        if (destroyed) return;
        params.state = { ...window.structuredClone(stripSecret(game, 0)), newTurn: true };
        app.$forceUpdate();
        await app.$nextTick();
    }
    let storage: Storage | undefined;
    try {
        storage = localStorage;
    } catch {
        /* Saving is optional. */
    }
    const controller = await createTutorial({
        ...lesson,
        storage,
        onProgress,
        async move(state, action) {
            const frames: GameState[] = [];
            const result = lesson.move(state, action, (frame) => frames.push(frame));
            if (animate)
                for (const frame of frames) {
                    if (destroyed) break;
                    await present(frame);
                    await new Promise<void>((resolve) => {
                        finishFrame = resolve;
                        timer = window.setTimeout(
                            resolve,
                            window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 450
                        );
                    });
                    finishFrame = undefined;
                }
            return result;
        },
    });
    async function play(action: Action) {
        if (destroyed || latest.busy || latest.completed || latest.canContinue) return;
        animate = true;
        try {
            await controller.play(action);
        } finally {
            animate = false;
        }
    }
    let controlStep = -1;
    const off = controller.subscribe((snapshot) => {
        latest = snapshot;
        params.tutorialCity = (
            { first: 'Essen', second: 'Duisburg', third: 'Dusseldorf', seventh: 'Kassel' } as Record<string, string>
        )[lesson.steps[snapshot.step]?.id ?? ''];
        params.interactionDisabled = snapshot.busy || snapshot.completed || snapshot.canContinue;
        if (previous !== snapshot.state) {
            previous = snapshot.state;
            void present(snapshot.state.game);
            const player = snapshot.state.game.players[0];
            summary.replaceChildren();
            for (const text of [
                `Germany · Classic rules · Round ${snapshot.state.game.round}`,
                `Cash: $${player.money}`,
                `Cities: ${player.cities.length}`,
                `Plant output: ${player.powerPlants.reduce((n, p) => n + p.citiesPowered, 0)}`,
                `Fuel: ${player.coalLeft} coal · ${player.oilLeft} oil`,
            ]) {
                const item = document.createElement('span');
                item.textContent = text;
                summary.append(item);
            }
        }
        if (controlStep !== snapshot.step) {
            controlStep = snapshot.step;
            controls.replaceChildren();
            for (const choice of lesson.choices(snapshot.state, lesson.steps[snapshot.step]?.id ?? '')) {
                const button = document.createElement('button');
                button.type = 'button';
                button.textContent = choice.label;
                button.onclick = () => {
                    void play(choice.action);
                };
                controls.append(button);
            }
            controls.hidden = !controls.childElementCount;
        }
        controls.querySelectorAll('button').forEach((button) => {
            button.disabled = snapshot.busy || snapshot.completed;
        });
        app.$forceUpdate();
    });
    const removeGuide = mountTutorialGuide(guide, controller, { nextChapter });
    return () => {
        destroyed = true;
        clearTimeout(timer);
        finishFrame?.();
        removeGuide();
        off();
        controller.destroy();
        emitter.removeAllListeners();
        app.$destroy();
        target.replaceChildren();
    };
};
