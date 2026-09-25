// Keep player names and illustrated plants opaque while translating complete entries.
export function localizeJournal(entry, translate, findPlant) {
    const root = document.createElement('span');
    root.innerHTML = entry;
    // Engine entries put names in badges. Only top-level prose can mention a plant;
    // never run the plant matcher through badge contents or HTML attributes.
    for (const child of Array.from(root.childNodes)) {
        if (child.nodeType !== 3) continue;
        const numberElement = child.nextSibling;
        if (
            /Power Plant\s+$/i.test(child.data) &&
            numberElement?.nodeName === 'B' &&
            /^\d+$/.test(numberElement.textContent)
        ) {
            const number = Number(numberElement.textContent);
            if (findPlant(number)) {
                const marker = document.createElement('span');
                marker.setAttribute('data-journal-plant', String(number));
                numberElement.replaceWith(marker);
            }
        }
        const pattern = /Power Plant\s+(\d+)/gi;
        const fragment = document.createDocumentFragment();
        let offset = 0;
        let match;
        while ((match = pattern.exec(child.data))) {
            if (!findPlant(Number(match[1]))) continue;
            fragment.append(document.createTextNode(child.data.slice(offset, match.index) + 'Power Plant '));
            const marker = document.createElement('span');
            marker.setAttribute('data-journal-plant', String(Number(match[1])));
            fragment.append(marker);
            offset = match.index + match[0].length;
        }
        if (offset) {
            fragment.append(document.createTextNode(child.data.slice(offset)));
            child.replaceWith(fragment);
        }
    }
    const slots = [];
    let source = '';
    for (const child of Array.from(root.childNodes)) {
        if (child.nodeType === 3) {
            source += child.textContent;
            continue;
        }
        source += `⟪${slots.length}⟫`;
        if (child.hasAttribute('data-journal-plant')) {
            slots.push({ plant: findPlant(Number(child.getAttribute('data-journal-plant'))) });
        } else {
            // First element is the player badge in move entries. Never translate it.
            if (slots.length > 0 && !child.hasAttribute('data-bgs-player')) {
                const walker = document.createTreeWalker(child, NodeFilter.SHOW_TEXT);
                while (walker.nextNode()) walker.currentNode.data = translate(walker.currentNode.data);
            }
            slots.push({ html: child.outerHTML });
        }
    }
    return translate(source)
        .split(/(⟪\d+⟫)/)
        .filter(Boolean)
        .map((part) => {
            const slot = /^⟪(\d+)⟫$/.exec(part);
            if (slot && slots[Number(slot[1])]) return slots[Number(slot[1])];
            const text = document.createElement('span');
            text.textContent = part;
            return { html: text.innerHTML };
        });
}
