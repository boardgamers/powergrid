import type { ChatMessage } from '@boardgamers/protocol/chat';
import { applyMention, ChatController, chatSegments, mentionQueryAt } from '@boardgamers/protocol/chat';
import type { ViewerEmitter } from '@boardgamers/protocol/viewer';
import { attachChat } from '@boardgamers/protocol/viewer';
import { playerColors } from 'powergrid-engine/src/gamestate';
type ChatEmitter = Pick<ViewerEmitter<any, any>, 'on' | 'emit'>;
export function mountGameChat(emitter: ViewerEmitter<any, any>, host: Element): () => void {
    const chat = new ChatController();
    const detach = attachChat(emitter, chat);
    const cleanup: (() => void)[] = [detach];
    let disposed = false;
    const panel = document.createElement('details');
    panel.className = 'bgs-game-chat';
    panel.open = true;
    panel.innerHTML =
        '<summary>Chat</summary><div class="chat-messages" role="log" aria-label="Game chat"></div><div class="chat-composer"><input type="text" aria-label="Chat message" placeholder="Message…" autocomplete="off"><button type="button">Send</button></div><div class="chat-status" role="status"></div>';
    const style = document.createElement('style');
    style.textContent = `
.bgs-game-chat{box-sizing:border-box;font:14px/1.4 Arial,sans-serif;border:1px solid #a2aa82;border-radius:3px;margin:8px 0;padding:8px 12px;background:#f3f0dc;color:#263521}
.bgs-game-chat summary{cursor:pointer;font-weight:650;border-radius:3px;width:fit-content;padding:2px 4px;margin:-2px -4px}
.bgs-game-chat summary:hover{color:#126778}
.bgs-game-chat summary:focus-visible,.bgs-game-chat button:focus-visible{outline:2px solid #247d8c;outline-offset:3px}
.bgs-game-chat .chat-messages{max-height:250px;overflow:auto;overscroll-behavior:auto;margin:6px 0 8px}
.bgs-game-chat article{padding:5px 0;border-bottom:1px solid #75818d26;white-space:pre-wrap;overflow-wrap:anywhere}
.bgs-game-chat article strong{padding:0 3px;font-weight:bold}
.bgs-game-chat article:last-child{border-bottom:0}
.bgs-game-chat time{font-size:12px;color:#536e77;margin-left:8px;white-space:nowrap}
.bgs-game-chat .chat-composer{display:flex;gap:6px;align-items:center;margin:0}
.bgs-game-chat input{flex:1;min-width:0;box-sizing:border-box;height:30px;background:#f3f5eb;color:#263521;border:1px solid #899997;border-radius:2px;padding:4px 7px;font:14px Arial,sans-serif}
.bgs-game-chat input::placeholder{color:#637477}
.bgs-game-chat input:focus{outline:2px solid #527f89;outline-offset:1px}
.bgs-game-chat button{box-sizing:border-box;height:30px;cursor:pointer;border:1px solid #7f8c8d;border-radius:3px;background:#dddeda;color:#172d34;padding:3px 12px;font:14px Arial,sans-serif}
.bgs-game-chat button:hover:not(:disabled){background:#c8d3d0}
.bgs-game-chat button:disabled{color:#788786;border-color:#b0bcb8;background:#dce3df;cursor:default}
.bgs-game-chat .chat-mention{height:auto;padding:0 2px;border:0;background:transparent;color:inherit;font:inherit;font-weight:bold;text-decoration:underline}
.bgs-game-chat article a{color:inherit;text-decoration:underline}
.chat-suggestions{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}
.chat-suggestions:empty{display:none}
.chat-suggestions button[aria-pressed="true"]{outline:2px solid #527f89}
.bgs-game-chat .chat-status{font-size:12px;margin-top:6px}
.bgs-game-chat .chat-status:empty{display:none}
.chat-shortcut{position:fixed;left:16px;bottom:max(16px,env(safe-area-inset-bottom));z-index:900;padding:7px 12px;border:1px solid #6a8589;border-radius:3px;background:#263521;color:#fff;font:600 14px Arial,sans-serif;cursor:pointer;box-shadow:0 2px 6px #0003}
.chat-shortcut[hidden]{display:none}
.game-feed-tabs{display:none}
@media(max-width:700px){
.game-feed-tabs{display:flex;gap:4px;margin-top:8px}
.game-feed-tabs button{border:1px solid #a2aa82;border-radius:3px 3px 0 0;padding:7px 14px;background:#e7ead7;color:#263521;font:600 14px Arial,sans-serif;cursor:pointer}
.game-feed-tabs button[aria-pressed="true"]{background:#f3f0dc;border-bottom:3px solid #526f32}
.game-feed-tabs button:focus-visible{outline:2px solid #247d8c;outline-offset:2px}
.journal-and-chat[data-feed="chat"]>.inline-game-log,.journal-and-chat[data-feed="journal"]>.chat-host{display:none}
}
.chat-shortcut:hover{background:#315966}
.chat-shortcut:focus-visible{outline:2px solid #fff;outline-offset:2px}

`;
    panel.append(style);
    const slot = host.querySelector('.chat-host');
    if (slot) slot.append(panel);
    else host.insertAdjacentElement('afterend', panel);
    const feeds = host.querySelector('.journal-and-chat') as HTMLElement | null;
    const tabs = document.createElement('nav');
    tabs.className = 'game-feed-tabs';
    tabs.setAttribute('aria-label', 'Chat and journal');
    const chatTab = document.createElement('button');
    const journalTab = document.createElement('button');
    chatTab.type = journalTab.type = 'button';
    chatTab.textContent = 'Chat';
    journalTab.textContent = 'Journal';
    tabs.append(chatTab, journalTab);
    host.querySelector('.chat-tabs-host')?.append(tabs);
    function selectFeed(feed: 'chat' | 'journal'): void {
        if (feeds) feeds.dataset.feed = feed;
        chatTab.setAttribute('aria-pressed', String(feed === 'chat'));
        journalTab.setAttribute('aria-pressed', String(feed === 'journal'));
    }
    selectFeed('chat');
    chatTab.onclick = () => {
        selectFeed('chat');
        panel.open = true;
        requestAnimationFrame(read);
    };
    journalTab.onclick = () => selectFeed('journal');
    const list = panel.querySelector('.chat-messages') as HTMLDivElement;
    const input = panel.querySelector('input') as HTMLInputElement;
    const button = panel.querySelector('button') as HTMLButtonElement;
    const status = panel.querySelector('.chat-status') as HTMLDivElement;
    let messages: readonly ChatMessage[] = [];
    let players: { id: number; name: string; color?: string }[] = [];
    let localPlayer: number | undefined;
    cleanup.push(
        emitter.on('state', (state) => {
            players = state?.players || [];
            render();
        })
    );
    cleanup.push(
        emitter.on('gamelog', ({ data }: any) => {
            if (data?.state) {
                players = data.state.players || [];
                render();
            }
        })
    );
    cleanup.push(
        emitter.on('player', (player) => {
            localPlayer = player?.index;
            render();
        })
    );
    let following = true;
    let followFrame: number | undefined;
    let unread: readonly string[] = [];
    const summary = panel.querySelector('summary')!;
    const shortcut = document.createElement('button');
    shortcut.type = 'button';
    shortcut.className = 'chat-shortcut';
    shortcut.hidden = true;
    (feeds || panel).insertAdjacentElement('afterend', shortcut);
    let chatVisible = false;
    function updateShortcut(): void {
        const count = chat.unread;
        const label = count ? `Chat · ${count} unread` : 'Chat';
        shortcut.textContent = label;
        shortcut.setAttribute('aria-label', `Open ${label}`);
        summary.textContent = label;
        chatTab.textContent = label;
        shortcut.hidden = chatVisible;
    }
    shortcut.onclick = () => {
        selectFeed('chat');
        panel.open = true;
        requestAnimationFrame(() => {
            const firstUnread = Array.from(list.children).find((row) =>
                unread.includes((row as HTMLElement).dataset.id || '')
            );
            if (firstUnread) firstUnread.scrollIntoView({ block: 'center' });
            else panel.scrollIntoView({ block: 'center' });
            summary.focus({ preventScroll: true });
            read();
        });
    };
    const visibility = new IntersectionObserver(
        (entries) => {
            for (const entry of entries) {
                if (entry.target === panel) {
                    chatVisible =
                        entry.isIntersecting &&
                        entry.intersectionRect.height >=
                            Math.min(panel.open ? 80 : 20, entry.boundingClientRect.height);
                }
            }
            updateShortcut();
            read();
        },
        { threshold: Array.from({ length: 21 }, (_, i) => i / 20) }
    );
    visibility.observe(panel);
    function controls(): void {
        const state = chat.snapshot;
        input.disabled = !state.canSend || state.disabled;
        button.disabled = input.disabled || !!state.pending || !state.draft.trim();
        if (input.value !== state.draft) input.value = state.draft;
        const reasons: Record<string, string> = {
            'not-logged-in': 'Sign in to chat',
            'not-confirmed': 'Confirm your account to chat',
            'not-a-player': 'Only players can send messages',
            'chat-disabled': 'Chat disabled',
            'no-game': 'Chat will be available when the game starts',
        };
        status.textContent =
            state.error ||
            (state.pending
                ? 'Sending…'
                : state.disabled
                ? 'Chat disabled'
                : !state.enabled
                ? 'Chat is connecting…'
                : !state.canSend
                ? reasons[state.reason] || 'Chat is read-only'
                : '');
    }
    function read(): void {
        if (disposed || !panel.open || document.visibilityState !== 'visible' || !document.hasFocus()) {
            return;
        }
        const bounds = list.getBoundingClientRect();
        if (!bounds.width || !bounds.height) return;
        if (!bounds.width || !bounds.height) return;
        const visible = Array.from(list.children).filter((el) => {
            const r = el.getBoundingClientRect();
            return r.bottom <= Math.min(bounds.bottom, window.innerHeight) + 1 && r.top >= Math.max(bounds.top, 0);
        });
        const id = (visible[visible.length - 1] as HTMLElement)?.dataset.id;
        if (id) chat.markRead(id);
    }
    function render(): void {
        const scrollTop = list.scrollTop;
        list.textContent = '';
        for (const message of messages) {
            const row = document.createElement('article');
            row.dataset.id = message._id || '';
            const author = document.createElement('strong');
            author.textContent = message.author || 'Game';
            const index =
                message.playerIndex ??
                (message.author === 'You' ? localPlayer : players.find((p) => p.name === message.author)?.id);
            if (index !== undefined && playerColors[index]) {
                author.style.backgroundColor = players.find((p) => p.id === index)?.color || playerColors[index];
                author.style.color = author.style.backgroundColor === 'brown' ? '#fff' : '#111';
            }
            row.append(author, document.createTextNode(' '));
            appendMessage(row, message);
            if (message.createdAt) {
                const time = document.createElement('time');
                const date = new Date(message.createdAt);
                if (!isNaN(date.getTime())) {
                    time.textContent = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    time.title = date.toLocaleString();
                    row.append(time);
                }
            }

            list.append(row);
        }
        if (following) {
            list.scrollTop = list.scrollHeight;
            // Vue may move the board and feeds during the same state update.
            if (followFrame !== undefined) cancelAnimationFrame(followFrame);
            followFrame = requestAnimationFrame(() => {
                followFrame = undefined;
                if (!disposed) {
                    list.scrollTop = list.scrollHeight;
                    read();
                }
            });
        } else list.scrollTop = scrollTop;
        updateShortcut();
        read();
    }
    function appendMessage(row: HTMLElement, message: ChatMessage): void {
        for (const segment of message.segments || [{ kind: 'text', text: message.text }]) {
            if (segment.kind === 'link') {
                const link = document.createElement('a');
                link.href = segment.url;
                link.textContent = segment.text;
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                row.append(link);
            } else if (segment.kind === 'mention') {
                const mention = document.createElement('button');
                mention.type = 'button';
                mention.className = 'chat-mention';
                mention.textContent = '@' + segment.name;
                const player = chat.snapshot.mentions.find((p) => p.id === segment.id);
                if (player?.playerIndex !== undefined)
                    mention.onclick = () => emitter.emit('player:clicked', { index: player.playerIndex! });
                else mention.disabled = true;
                row.append(mention);
            } else row.append(document.createTextNode(segment.text));
        }
    }
    const suggestions = document.createElement('div');
    suggestions.className = 'chat-suggestions';
    suggestions.setAttribute('aria-label', 'Mention suggestions');
    panel.querySelector('.chat-composer')!.insertAdjacentElement('afterend', suggestions);
    let selected = 0;
    let candidates: ReturnType<ChatController['suggestions']> = [];
    let query: ReturnType<typeof mentionQueryAt> = null;
    function chooseMention(index: number): void {
        const person = candidates[index];
        if (!query || !person) return;
        const result = applyMention(input.value, query, person.name);
        chat.setDraft(result.text);
        input.focus();
        input.setSelectionRange(result.caret, result.caret);
        suggestions.replaceChildren();
        candidates = [];
        query = null;
    }
    function suggest(): void {
        query = mentionQueryAt(input.value, input.selectionStart ?? input.value.length);
        candidates = query ? chat.suggestions(query.query).slice(0, 6) : [];
        selected = Math.min(selected, Math.max(0, candidates.length - 1));
        suggestions.replaceChildren();
        candidates.forEach((candidate, index) => {
            const option = document.createElement('button');
            option.type = 'button';
            option.textContent = '@' + candidate.name;
            option.setAttribute('aria-pressed', String(index === selected));
            option.onmousedown = (event) => event.preventDefault();
            option.onclick = () => chooseMention(index);
            suggestions.append(option);
        });
    }
    button.onclick = () => chat.submit();
    input.oninput = () => {
        selected = 0;
        chat.setDraft(input.value);
        suggest();
    };
    input.onclick = suggest;
    input.onkeydown = (event) => {
        if (event.isComposing) return;
        if (candidates.length && ['ArrowDown', 'ArrowUp', 'Enter', 'Tab', 'Escape'].includes(event.key)) {
            event.preventDefault();
            event.stopPropagation();
            if (event.key === 'Escape') {
                candidates = [];
                suggestions.replaceChildren();
            } else if (event.key === 'Enter' || event.key === 'Tab') chooseMention(selected);
            else {
                selected = (selected + (event.key === 'ArrowDown' ? 1 : candidates.length - 1)) % candidates.length;
                suggest();
            }
        } else if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            event.stopPropagation();
            chat.submit();
        }
    };
    cleanup.push(
        chat.subscribe((state) => {
            const changed = messages !== state.messages;
            messages = state.messages;
            unread = state.unreadIds;
            controls();
            if (changed) render();
            else updateShortcut();
        })
    );
    list.onscroll = () => {
        if (followFrame === undefined && list.clientHeight)
            following = list.scrollHeight - list.scrollTop - list.clientHeight < 32;
        read();
    };
    panel.ontoggle = () => {
        chat.setOpen(panel.open);
        if (!disposed && panel.open && following) {
            list.scrollTop = list.scrollHeight;
        }
        read();
    };
    window.addEventListener('scroll', read, { passive: true });
    window.addEventListener('focus', read);
    window.addEventListener('resize', read);
    const sizing = new ResizeObserver(() => {
        if (following && list.clientHeight) list.scrollTop = list.scrollHeight;
        updateShortcut();
        read();
    });
    sizing.observe(panel);
    sizing.observe(list);
    document.addEventListener('visibilitychange', read);
    controls();
    return () => {
        disposed = true;
        if (followFrame !== undefined) cancelAnimationFrame(followFrame);
        cleanup.forEach((dispose) => dispose());
        visibility.disconnect();
        sizing.disconnect();
        window.removeEventListener('scroll', read);
        window.removeEventListener('focus', read);
        window.removeEventListener('resize', read);
        document.removeEventListener('visibilitychange', read);
        panel.remove();
        shortcut.remove();
        tabs.remove();
    };
}

export function installLocalChat(emitter: ChatEmitter): void {
    let seat = 0;
    let roster: { id: string; name: string; playerIndex: number }[] = [];
    emitter.on('player', (player) => {
        seat = player.index ?? 0;
    });
    emitter.on('state', (state) => {
        roster = (state?.players || []).map((player: any, index: number) => ({
            id: String(index),
            name: player.name || `Player ${index + 1}`,
            playerIndex: index,
        }));
        emitter.emit('chat:state', { canSend: true, mentions: roster.filter((player) => player.playerIndex !== seat) });
    });
    emitter.emit('chat:state', { canSend: true });
    emitter.emit('chat:messages', [
        {
            _id: '000000000000000000000001',
            type: 'system',
            author: 'Playtest',
            text: 'Local chat preview. Messages stay in this browser.',
            createdAt: new Date().toISOString(),
        },
    ]);
    let next = 2;
    emitter.on('chat:send', ({ text, requestId }) => {
        emitter.emit('chat:appended', [
            {
                _id: (next++).toString(16).padStart(24, '0'),
                type: 'text',
                author: 'You',
                playerIndex: seat,
                text,
                segments: chatSegments(text, new Map(roster.map((player) => [player.name, player.id])), true),
                createdAt: new Date().toISOString(),
            },
        ]);
        emitter.emit('chat:result', { requestId, ok: true });
    });
}
