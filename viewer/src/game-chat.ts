import { ChatController, ChatMessage, chatSegments } from '@boardgamers/protocol/chat';
import { mountChat } from '@boardgamers/protocol/chat/dom';
import { attachChat, ViewerEmitter } from '@boardgamers/protocol/viewer';
import { playerColors } from 'powergrid-engine/src/gamestate';
type ChatEmitter = Pick<ViewerEmitter<any, any>, 'on' | 'emit'>;
export function mountGameChat(emitter: ViewerEmitter<any, any>, host: Element): () => void {
    const chat = new ChatController();
    const detach = attachChat(emitter, chat);
    const slot = host.querySelector<HTMLElement>('.chat-host') || document.createElement('div');
    if (!slot.parentElement) host.insertAdjacentElement('afterend', slot);
    const style = document.createElement('style');
    style.textContent = `
.bgs-game-chat{box-sizing:border-box;font:14px/1.4 Arial,sans-serif;border:1px solid #a2aa82;border-radius:3px;margin:8px 0;padding:8px 12px;background:#f3f0dc;color:#263521}
.bgs-game-chat summary{cursor:pointer;font-weight:650;border-radius:3px;width:fit-content;padding:2px 4px;margin:-2px -4px}
.bgs-game-chat summary:hover{color:#126778}
.bgs-game-chat summary:focus-visible,.bgs-game-chat button:focus-visible{outline:2px solid #247d8c;outline-offset:3px}
.bgs-game-chat .chat-day{display:flex;align-items:center;gap:8px;margin:12px 0 6px;font-size:.85em;opacity:.8}
.bgs-game-chat .chat-day::before,.bgs-game-chat .chat-day::after{content:"";flex:1;border-top:1px solid currentColor;opacity:.3}
.bgs-game-chat .chat-day time{margin:0;color:inherit;font-size:inherit}
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
    slot.append(style);
    let players: { id: number; name: string; color?: string; faction?: string }[] = [];
    let localPlayer: number | undefined;
    let chatVisible = false;
    const shortcut = document.createElement('button');
    shortcut.type = 'button';
    shortcut.className = 'chat-shortcut';
    shortcut.hidden = true;
    (host.querySelector('.chat-tabs-host') || slot).append(shortcut);
    const feeds = host.querySelector<HTMLElement>('.journal-and-chat');
    const tabs = document.createElement('nav');
    tabs.className = 'game-feed-tabs';
    tabs.setAttribute('aria-label', 'Chat and journal');
    const chatTab = document.createElement('button');
    const journalTab = document.createElement('button');
    chatTab.type = journalTab.type = 'button';
    journalTab.textContent = 'Journal';
    tabs.append(chatTab, journalTab);
    host.querySelector('.chat-tabs-host')?.append(tabs);
    function selectFeed(feed: 'chat' | 'journal') {
        if (feeds) feeds.dataset.feed = feed;
        chatTab.setAttribute('aria-pressed', String(feed === 'chat'));
        journalTab.setAttribute('aria-pressed', String(feed === 'journal'));
    }
    selectFeed('chat');
    const view = mountChat(slot, {
        chat,
        styles: false,
        openPlayer: (index) => emitter.emit('player:clicked', { index }),
        renderAuthor,
        onVisibilityChange(visible) {
            chatVisible = visible;
            updateShortcut();
        },
    });
    function renderAuthor(message: ChatMessage): Node {
        const author = document.createElement('strong');
        author.textContent = message.author || 'Game';
        const index =
            message.playerIndex ??
            (message.author === 'You' ? localPlayer : players.find((p) => p.name === message.author)?.id);
        if (index !== undefined && playerColors[index]) {
            author.style.backgroundColor = players.find((p) => p.id === index)?.color || playerColors[index];
            author.style.color = author.style.backgroundColor === 'brown' ? '#fff' : '#111';
        }
        return author;
    }
    function updateShortcut() {
        const count = chat.unread;
        const label = count ? `Chat · ${count} unread` : 'Chat';
        shortcut.textContent = label;
        shortcut.hidden = chatVisible;
        shortcut.setAttribute('aria-label', `Open ${label}`);
        chatTab.textContent = label;
    }
    shortcut.onclick = () => {
        selectFeed('chat');
        view.open();
    };
    const dispose = [
        detach,
        chat.subscribe(updateShortcut),
        emitter.on('state', (state) => {
            players = (state?.players || []).map((player: any, index: number) => ({ ...player, id: index }));
            view.refresh();
        }),
        emitter.on('gamelog', ({ data }: any) => {
            if (data?.state) {
                players = (data.state.players || []).map((player: any, index: number) => ({ ...player, id: index }));
                view.refresh();
            }
        }),
        emitter.on('player', (player) => {
            localPlayer = player?.index;
            view.refresh();
        }),
    ];
    chatTab.onclick = () => {
        selectFeed('chat');
        chat.setOpen(true);
        view.refresh();
    };
    journalTab.onclick = () => {
        selectFeed('journal');
        view.refresh();
    };
    dispose.push(() => tabs.remove());
    return () => {
        dispose.forEach((cleanup) => cleanup());
        view.destroy();
        shortcut.remove();
        style.remove();
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
