import { element } from './dom.js';
function loadLeaflet() {
    if (window.L)
        return window.L;
    element('map-error').textContent = 'The map could not start. Refresh this page to try again.';
    element('map-error').hidden = false;
    element('draw').disabled = true;
    throw new Error('Leaflet is unavailable');
}
// Runtime Leaflet stays in dist/vendor; npm supplies its TypeScript declarations.
export const L = loadLeaflet();
//# sourceMappingURL=leaflet.js.map