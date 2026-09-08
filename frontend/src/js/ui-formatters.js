export function getTimeStamp(value) {
    if (!value) return 0;
    if (typeof value === 'number') {
        return Number.isFinite(value) && value > 0 ? value : 0;
    }
    if (value instanceof Date) {
        const time = value.getTime();
        return Number.isFinite(time) ? time : 0;
    }
    if (typeof value === 'string') {
        const numeric = Number(value);
        if (Number.isFinite(numeric) && numeric > 0 && /^\d+$/.test(value.trim())) {
            return numeric;
        }
        const stamp = Date.parse(value);
        return Number.isFinite(stamp) ? stamp : 0;
    }
    return 0;
}

export function formatRelativeTime(value) {
    const stamp = getTimeStamp(value);
    if (!stamp) return 'recently';

    const deltaMs = Date.now() - stamp;
    if (deltaMs < 60 * 1000) return 'just now';

    const minutes = Math.floor(deltaMs / (60 * 1000));
    if (minutes < 60) return `${minutes}m ago`;

    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;

    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}
