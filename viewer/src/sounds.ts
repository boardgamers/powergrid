type Note = [number, number, number, number, number?];
type Cue = { label: string; notes: Note[] };
export const soundCues: Record<string, Cue> = {
    build: {
        label: 'Connect a city',
        notes: [
            [0, 0.1, 0, 0.12, 1500],
            [0.08, 0.25, 95, 0.1, 45],
            [0.18, 0.14, 360, 0.05, 500],
        ],
    },
    fuel: {
        label: 'Buy fuel',
        notes: [
            [0, 0.12, 0, 0.1, 1100],
            [0.1, 0.13, 0, 0.08, 600],
            [0.12, 0.16, 120, 0.06, 65],
        ],
    },
    bid: { label: 'Auction bid', notes: [[0, 0.08, 400, 0.07, 550]] },
    plant: {
        label: 'Power plant',
        notes: [
            [0, 0.15, 110, 0.09],
            [0.07, 0.23, 220, 0.07, 330],
        ],
    },
    power: {
        label: 'Generate electricity',
        notes: [
            [0, 0.45, 60, 0.09, 120],
            [0.05, 0.4, 121, 0.05, 240],
            [0.1, 0.35, 0, 0.04, 1300],
        ],
    },
};
let context: AudioContext | undefined;
let enabled = true;
export function setSoundEnabled(value: boolean): void {
    enabled = value;
}
export function playSound(name: string): void {
    if (!enabled || !soundCues[name] || typeof window === 'undefined') {
        return;
    }
    if (typeof navigator !== 'undefined') {
        const activation = (navigator as Navigator & { userActivation?: { hasBeenActive: boolean } }).userActivation;
        if (activation && !activation.hasBeenActive) {
            return;
        }
    }
    const Audio = window.AudioContext;
    if (!Audio) {
        return;
    }
    context = context || new Audio();
    const ctx = context;
    void ctx
        .resume()
        .then(() => {
            if (!enabled || ctx.state !== 'running') {
                return;
            }
            for (const [offset, duration, frequency, volume, endFrequency] of soundCues[name].notes) {
                const start = ctx.currentTime + offset;
                const gain = ctx.createGain();
                gain.gain.setValueAtTime(0.0001, start);
                gain.gain.exponentialRampToValueAtTime(volume, start + 0.008);
                gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
                gain.connect(ctx.destination);
                if (frequency === 0) {
                    const buffer = ctx.createBuffer(1, Math.ceil(ctx.sampleRate * duration), ctx.sampleRate);
                    const samples = buffer.getChannelData(0);
                    for (let i = 0; i < samples.length; i++) {
                        samples[i] = Math.random() * 2 - 1;
                    }
                    const source = ctx.createBufferSource();
                    source.buffer = buffer;
                    const filter = ctx.createBiquadFilter();
                    filter.type = 'lowpass';
                    filter.frequency.value = endFrequency || 900;
                    source.connect(filter);
                    filter.connect(gain);
                    source.start(start);
                    source.stop(start + duration);
                } else {
                    const oscillator = ctx.createOscillator();
                    oscillator.type = 'sine';
                    oscillator.frequency.setValueAtTime(frequency, start);
                    oscillator.frequency.exponentialRampToValueAtTime(endFrequency || frequency, start + duration);
                    oscillator.connect(gain);
                    oscillator.start(start);
                    oscillator.stop(start + duration);
                }
            }
        })
        .catch(() => undefined);
}

export function installActionSounds(emitter: { on: (event: string, fn: (value: any) => void) => unknown }): void {
    let previous: string[] | undefined;
    let replaying = false;
    emitter.on('update:preference', (pref) => {
        if (pref?.name === 'sound') {
            setSoundEnabled(pref.value);
        }
    });
    emitter.on('preferences', (prefs) => {
        if (typeof prefs?.sound === 'boolean') {
            setSoundEnabled(prefs.sound);
        }
    });
    emitter.on('replay:start', () => {
        replaying = true;
    });
    emitter.on('replay:end', () => {
        replaying = false;
        previous = undefined;
    });
    const receiveState = (state: any) => {
        const entries = state?.log || [];
        const next = entries.map((entry: any) => JSON.stringify(entry));
        const extendsHistory =
            previous && previous.length < next.length && previous.every((entry, i) => entry === next[i]);
        const from = previous?.length || 0;
        previous = next;
        if (!extendsHistory || replaying) {
            return;
        }
        const cues = entries
            .slice(from)
            .map((entry: any) => cueForEntry(entry))
            .filter(Boolean);
        // Reconnection can deliver a whole round: play only the most recent event.
        const cue = cues[cues.length - 1];
        if (cue) {
            playSound(cue);
        }
    };
    emitter.on('state', receiveState);
    emitter.on('gamelog', (event) => {
        if (event?.data?.state) {
            receiveState(event.data.state);
        }
    });
}

export function mountSoundTests(emitter: { emit: (event: string, value: any) => unknown }): void {
    const panel = document.createElement('details');
    panel.style.cssText =
        'position:relative;z-index:5;padding:10px 16px;margin:8px;background:#172638;color:#f0f4f8;border:1px solid #56718a;border-radius:8px;font:14px system-ui';
    const summary = document.createElement('summary');
    summary.textContent = 'Playtest tools · sounds';
    panel.append(summary);
    const label = document.createElement('label');
    label.style.margin = '10px';
    const toggle = document.createElement('input');
    toggle.type = 'checkbox';
    toggle.checked = true;
    toggle.onchange = () => {
        setSoundEnabled(toggle.checked);
        emitter.emit('preferences', { sound: toggle.checked });
    };
    label.append(toggle, ' Game sounds');
    panel.append(label);
    for (const [name, cue] of Object.entries(soundCues)) {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = cue.label;
        button.style.cssText =
            'margin:8px 4px;padding:7px 12px;color:#f0f4f8;background:#294663;border:1px solid #7391ad;border-radius:5px;cursor:pointer';
        button.onclick = () => playSound(name);
        panel.append(button);
    }
    document.body.prepend(panel);
}
function cueForEntry(entry: any): string | undefined {
    return (
        {
            Build: 'build',
            BuyResource: 'fuel',
            Bid: 'bid',
            ChoosePowerPlant: 'plant',
            UsePowerPlant: 'power',
        } as Record<string, string>
    )[entry.move?.name];
}
