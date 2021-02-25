const ENTITY_MAP = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
    '/': '&#x2F;',
    '`': '&#x60;',
    '=': '&#x3D;',
}

/* Taken from https://github.com/janl/mustache.js/blob/master/mustache.js#L60 */
export default {
    escapeHtml (string) {
        return String(string).replace(/[&<>"'`=/]/g, (s) => ENTITY_MAP[s])
    },
}
