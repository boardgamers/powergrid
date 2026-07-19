// Formats a duration in milliseconds compactly, at a precision that suits the
// magnitude. Games range from a few minutes per player to correspondence games
// running for days, so the unit pair shifts with the size:
//   45s | 12m 34s | 3h 22m | 5d 3h
export function formatDuration(ms: number): string {
    if (!ms || ms < 0) {
        return '0s';
    }

    const totalSeconds = Math.floor(ms / 1000);
    const totalMinutes = Math.floor(totalSeconds / 60);
    const totalHours = Math.floor(totalMinutes / 60);
    const days = Math.floor(totalHours / 24);

    if (days > 0) {
        return `${days}d ${totalHours % 24}h`;
    }
    if (totalHours > 0) {
        return `${totalHours}h ${totalMinutes % 60}m`;
    }
    if (totalMinutes > 0) {
        return `${totalMinutes}m ${totalSeconds % 60}s`;
    }
    return `${totalSeconds}s`;
}
