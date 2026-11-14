import test from 'node:test';
import assert from 'node:assert/strict';
import {area, validPolygon, geoJSON, csv, unwrap} from '../dist/geometry.js';

const square=[{lat:0,lng:0},{lat:0,lng:1},{lat:1,lng:1},{lat:1,lng:0}];
test('spherical area of a one degree equatorial square',()=>{
  assert.ok(Math.abs(area(square)/1e6-12363.718)<1);
  assert.ok(validPolygon(square));
});
test('rejects crossed, collinear, duplicate and invalid boundaries',()=>{
  assert.equal(validPolygon([square[0],square[2],square[1],square[3]]),false);
  assert.equal(validPolygon([{lat:0,lng:0},{lat:0,lng:1},{lat:0,lng:2}]),false);
  assert.equal(validPolygon([square[0],square[1],square[1],square[3]]),false);
  assert.equal(validPolygon([{lat:NaN,lng:0},...square]),false);
});
test('GeoJSON has longitude first, closes its ring and uses counterclockwise winding',()=>{
  const points=[{lat:30,lng:10},{lat:31,lng:10},{lat:31,lng:11}];
  const json=geoJSON(points),ring=json.geometry.coordinates[0];
  assert.equal(json.type,'Feature');assert.equal(json.geometry.type,'Polygon');
  assert.deepEqual(ring[0],ring.at(-1));assert.equal(ring.length,4);
  assert.ok(ring.some(p=>p[0]===10&&p[1]===30));
  assert.ok(ring.slice(0,-1).reduce((s,a,i)=>{const b=ring[i+1];return s+a[0]*b[1]-b[0]*a[1];},0)>0);
});
test('handles a polygon crossing the antimeridian without inflating area',()=>{
  const p=[{lat:0,lng:179.5},{lat:0,lng:-179.5},{lat:1,lng:-179.5},{lat:1,lng:179.5}];
  assert.ok(validPolygon(p));assert.ok(Math.abs(area(p)-area(square))<1);
  assert.equal(unwrap(p)[1].lng,180.5);
  const ring=geoJSON(p).geometry.coordinates[0];
  assert.ok(Math.max(...ring.map(p=>p[0]))-Math.min(...ring.map(p=>p[0]))<2);
});
test('CSV names its coordinate order and preserves decimal precision',()=>{
  assert.equal(csv([{lat:32.12345678,lng:34.98765432}]),'vertex,latitude,longitude\r\n1,32.123457,34.987654\r\n');
});
