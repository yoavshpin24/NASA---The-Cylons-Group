export const EARTH_RADIUS = 6371008.8;
const rad = (n) => n * Math.PI / 180;
export const wrapLongitude = (n) => ((n + 180) % 360 + 360) % 360 - 180;
export function unwrap(points) {
    return points.map((p, i, all) => {
        let lng = p.lng;
        if (i) {
            const prev = all[i - 1].lng;
            lng = prev + wrapLongitude(lng - prev);
        }
        return { lat: p.lat, lng };
    }).reduce((out, p) => {
        if (out.length)
            p.lng = out.at(-1).lng + wrapLongitude(p.lng - out.at(-1).lng);
        out.push(p);
        return out;
    }, []);
}
export function area(points) {
    if (points.length < 3)
        return 0;
    let sum = 0;
    for (let i = 0; i < points.length; i++) {
        const a = points[i], b = points[(i + 1) % points.length];
        sum += rad(wrapLongitude(b.lng - a.lng)) * (2 + Math.sin(rad(a.lat)) + Math.sin(rad(b.lat)));
    }
    const sphere = 4 * Math.PI * EARTH_RADIUS ** 2;
    const measured = Math.abs(sum * EARTH_RADIUS ** 2 / 2) % sphere;
    return Math.min(measured, sphere - measured);
}
export function isSimple(points) {
    const p = unwrap(points), n = p.length;
    const cross = (a, b, c) => (b.lng - a.lng) * (c.lat - a.lat) - (b.lat - a.lat) * (c.lng - a.lng);
    const on = (a, b, c) => Math.abs(cross(a, b, c)) < 1e-10 && c.lng >= Math.min(a.lng, b.lng) - 1e-10 && c.lng <= Math.max(a.lng, b.lng) + 1e-10 && c.lat >= Math.min(a.lat, b.lat) - 1e-10 && c.lat <= Math.max(a.lat, b.lat) + 1e-10;
    const intersect = (a, b, c, d) => {
        const x = cross(a, b, c), y = cross(a, b, d), z = cross(c, d, a), w = cross(c, d, b);
        return (x * y < 0 && z * w < 0) || on(a, b, c) || on(a, b, d) || on(c, d, a) || on(c, d, b);
    };
    for (let i = 0; i < n; i++)
        for (let j = i + 1; j < n; j++) {
            if (j === i + 1 || (i === 0 && j === n - 1))
                continue;
            if (intersect(p[i], p[(i + 1) % n], p[j], p[(j + 1) % n]))
                return false;
        }
    return true;
}
export function validPolygon(points) {
    return points.length >= 3 && points.every(p => Number.isFinite(p.lat) && Number.isFinite(p.lng) && Math.abs(p.lat) <= 85.051129) && area(points) > 0.01 && isSimple(points);
}
export function geoJSON(points) {
    let ring = unwrap(points).map((p) => [Number(p.lng.toFixed(6)), Number(p.lat.toFixed(6))]);
    const signed = ring.reduce((sum, a, i) => { const b = ring[(i + 1) % ring.length]; return sum + a[0] * b[1] - b[0] * a[1]; }, 0);
    if (signed < 0)
        ring = ring.reverse();
    if (ring.length)
        ring.push([...ring[0]]);
    return { type: 'Feature', properties: { name: 'My polygon', area_m2: Math.round(area(points)) }, geometry: { type: 'Polygon', coordinates: [ring] } };
}
export function csv(points) {
    return 'vertex,latitude,longitude\r\n' + points.map((p, i) => `${i + 1},${p.lat.toFixed(6)},${wrapLongitude(p.lng).toFixed(6)}`).join('\r\n') + '\r\n';
}
//# sourceMappingURL=geometry.js.map