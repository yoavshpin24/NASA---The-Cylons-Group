import { area, wrapLongitude, unwrap, validPolygon, geoJSON, csv } from './geometry.js';
import { attachFarmland } from './farmland-layer.js';

const $ = id => document.getElementById(id);
const icon = name => `<svg><use href="#i-${name}"/></svg>`;
let points = [], backup = [], drawing = false, format = 'table', exportFormat = 'geojson', markers = [], toastTimer, searchController;
const storageKey = 'terra-polygon-v1';
const notify = message => { $('toast').textContent=message; $('toast').hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('toast').hidden=true,4500); };

if (!window.L) {
  $('map-error').textContent='The map could not start. Refresh this page to try again.';
  $('map-error').hidden=false;
  $('draw').disabled=true;
  throw new Error('Leaflet is unavailable');
}

const map = L.map('map',{zoomControl:false,doubleClickZoom:false,minZoom:2,maxZoom:19,worldCopyJump:true,maxBounds:[[-85.051129,-540],[85.051129,540]],maxBoundsViscosity:1}).setView([33.49,-6.5],10);
map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>');
L.control.scale({position:'bottomleft',imperial:false,maxWidth:90}).addTo(map);
const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxNativeZoom:18,maxZoom:19,attribution:'Imagery © Esri, Maxar, Earthstar Geographics, GIS User Community'});
const streets = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'});
satellite.addTo(map);
const farmland = attachFarmland(map, () => drawing);
const polygon = L.polygon([],{color:'#d3f3a2',weight:3,fillColor:'#c1e88a',fillOpacity:.2,interactive:false}).addTo(map);
const line = L.polyline([],{color:'#e0f7ba',weight:3,interactive:false}).addTo(map);
const ghost = L.polyline([],{color:'#e0f7ba',weight:1.5,dashArray:'4 6',opacity:.8,interactive:false}).addTo(map);
let loadedTiles=0, failedTiles=0;
for(const layer of [satellite,streets]) {
  layer.on('tileload',()=>{loadedTiles++;$('map-error').hidden=true;});
  layer.on('tileerror',()=>{failedTiles++;if(failedTiles>3&&loadedTiles===0)$('map-error').hidden=false;});
}

function save() {
  try { if(points.length) localStorage.setItem(storageKey,JSON.stringify(points.map(p=>({lat:p.lat,lng:wrapLongitude(p.lng)})))); else localStorage.removeItem(storageKey); }
  catch { /* Map and exports remain usable when browser storage is unavailable. */ }
}
function renderMarkers() {
  markers.forEach(m=>m.remove());
  markers=unwrap(points).map((p,i)=>{
    const marker=L.marker([p.lat,p.lng],{draggable:true,keyboard:true,title:`Vertex ${i+1}. Drag to adjust.`,icon:L.divIcon({className:`vertex-icon ${i===0?'first-vertex':''}`,html:String(i+1),iconSize:[21,21],iconAnchor:[10.5,10.5]})}).addTo(map);
    marker.on('click',e=>{L.DomEvent.stopPropagation(e);if(drawing&&i===0)finish();});
    let before;
    marker.on('dragstart',()=>{before={...points[i]};});
    marker.on('drag',()=>{const p=marker.getLatLng();points[i]={lat:p.lat,lng:p.lng};renderShape();renderData();});
    marker.on('dragend',()=>{
      if(!drawing&&!validPolygon(points)){points[i]=before;notify('That move creates an invalid boundary. Try another position.');}
      renderShape();renderMarkers();renderData();if(!drawing)save();
    });
    return marker;
  });
}
function renderShape() {
  const display=unwrap(points).map(p=>[p.lat,p.lng]);
  polygon.setLatLngs(points.length>=3?display:[]);
  polygon.setStyle({fillOpacity:drawing?.12:.23});
  line.setLatLngs(drawing&&points.length<3?display:[]);
  if(!drawing||!points.length)ghost.setLatLngs([]);
}
function renderData() {
  $('vertices').innerHTML=`${points.length} <small>points</small>`;
  const km=area(points)/1e6;
  $('area').innerHTML=points.length>=3?`${km<.01?(km*1e6).toLocaleString(undefined,{maximumFractionDigits:1}):km.toLocaleString(undefined,{maximumFractionDigits:2})} <small>${km<.01?'m²':'km²'}</small>`:'— <small>km²</small>';
  $('finish').disabled=points.length<3;
  $('undo').disabled=!points.length;
  $('clear').disabled=drawing||!points.length;
  $('copy').disabled=$('download').disabled=drawing||points.length<3;
  $('selection-state').textContent=drawing?'DRAWING':points.length?'AREA SELECTED':'NO AREA YET';
  $('selection-state').classList.toggle('ready',!drawing&&points.length>0);
  $('coordinate-note').textContent=format==='table'?'Latitude, longitude · 6 decimal places':'Longitude, latitude · closed polygon ring';
  if(!points.length){
    $('coordinate-content').innerHTML=`<div class="empty-state"><div class="empty-art">${icon('polygon')}<span class="orbit-dot"></span></div><strong>A few points. Endless possibilities.</strong><p>Your coordinates will appear here<br>as you draw on the map.</p></div>`;
  } else if(format==='table') {
    $('coordinate-content').innerHTML=`<table class="coordinate-table"><thead><tr><th>POINT</th><th>LATITUDE</th><th>LONGITUDE</th></tr></thead><tbody>${points.map((p,i)=>`<tr data-index="${i}"><td>${String(i+1).padStart(2,'0')}</td><td>${p.lat.toFixed(6)}</td><td>${wrapLongitude(p.lng).toFixed(6)}</td></tr>`).join('')}</tbody></table>`;
  } else {
    const pre=document.createElement('pre');pre.className='json-output';
    pre.textContent=points.length>=3?JSON.stringify(geoJSON(points),null,2):'Add at least 3 points to create a GeoJSON polygon.';
    $('coordinate-content').replaceChildren(pre);
  }
  if(drawing)$('draw-tip').textContent=points.length<3?`${points.length} point${points.length===1?'':'s'} placed · at least 3 needed.`:'Click the first point or press Enter to finish.';
}
function render() {renderShape();renderMarkers();renderData();}
function setDrawing(value) {
  drawing=value;
  farmland.onDrawingChange();
  $('draw').hidden=value;$('drawing-actions').hidden=!value;
  $('map').classList.toggle('map-drawing',value);
  $('draw-description').textContent=value?'Click on the map to add points to your boundary. Drag a point to adjust it.':'Place points on the map to outline an area. Close the shape to get its coordinates.';
  $('draw-tip').textContent=points.length?'Drag any vertex to refine your selection.':'Click to place points. Click the first to finish.';
  $('draw').querySelector('span').textContent=points.length?'Draw a new polygon':'Draw a polygon';
  render();
}
function start() {
  backup=points.map(p=>({...p}));points=[];$('map-hint').hidden=true;setDrawing(true);
  if(window.innerWidth<=720)$('map').scrollIntoView({behavior:'smooth',block:'center'});
}
function finish() {
  if(points.length<3){notify('Add at least three points to finish your polygon.');return;}
  if(!validPolygon(points)){notify('Your boundary crosses itself or has no area. Undo a point and try again.');return;}
  setDrawing(false);save();notify('Polygon ready. Drag a point to refine it, or export your coordinates.');
}
$('draw').addEventListener('click',start);
$('finish').addEventListener('click',finish);
$('undo').addEventListener('click',()=>{points.pop();ghost.setLatLngs([]);render();});
$('cancel').addEventListener('click',()=>{points=backup;setDrawing(false);});
$('clear').addEventListener('click',()=>{points=[];backup=[];setDrawing(false);save();$('map-hint').hidden=false;notify('Selection cleared. The world is your canvas again.');});
map.on('click',e=>{
  $('search-results').hidden=true;
  if(!drawing)return;
  let p={lat:e.latlng.lat,lng:e.latlng.lng};
  if(points.length){p.lng=points.at(-1).lng+wrapLongitude(p.lng-points.at(-1).lng);if(map.distance(points.at(-1),p)<.05)return;}
  points.push(p);render();
});
map.on('mousemove',e=>{
  const {lat,lng}=e.latlng,l=wrapLongitude(lng);
  $('cursor-coordinates').textContent=`${Math.abs(lat).toFixed(4)}° ${lat>=0?'N':'S'}   ${Math.abs(l).toFixed(4)}° ${l>=0?'E':'W'}`;
  if(drawing&&points.length)ghost.setLatLngs([points.at(-1),{lat,lng:points.at(-1).lng+wrapLongitude(lng-points.at(-1).lng)}]);
});
map.on('mouseout',()=>ghost.setLatLngs([]));

document.querySelectorAll('[data-format]').forEach(button=>button.addEventListener('click',()=>{
  format=button.dataset.format;
  document.querySelectorAll('[data-format]').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-selected',String(b===button));});
  $('coordinate-content').setAttribute('aria-labelledby',button.id);renderData();
}));
document.querySelectorAll('[data-export]').forEach(button=>button.addEventListener('click',()=>{
  exportFormat=button.dataset.export;
  document.querySelectorAll('[data-export]').forEach(b=>b.classList.toggle('active',b===button));
  $('download').setAttribute('aria-label',`Download ${exportFormat==='csv'?'CSV':'GeoJSON'}`);
}));
$('copy').addEventListener('click',async()=>{
  const text=format==='geojson'?JSON.stringify(geoJSON(points),null,2):points.map(p=>`${p.lat.toFixed(6)}, ${wrapLongitude(p.lng).toFixed(6)}`).join('\n');
  try { await navigator.clipboard.writeText(text);notify('Coordinates copied to clipboard.'); }
  catch {
    const textarea=document.createElement('textarea');textarea.value=text;textarea.style.cssText='position:fixed;left:-9999px';document.body.append(textarea);textarea.select();
    const copied=document.execCommand('copy');textarea.remove();notify(copied?'Coordinates copied to clipboard.':'Clipboard unavailable. Download your coordinates instead.');
  }
});
$('download').addEventListener('click',()=>{
  const text=exportFormat==='csv'?csv(points):JSON.stringify(geoJSON(points),null,2)+'\n';
  const blob=new Blob([text],{type:exportFormat==='csv'?'text/csv;charset=utf-8':'application/geo+json'});
  const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`terra-polygon.${exportFormat}`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  notify(`${exportFormat==='csv'?'CSV':'GeoJSON'} downloaded.`);
});

$('zoom-in').addEventListener('click',()=>map.zoomIn());
$('zoom-out').addEventListener('click',()=>map.zoomOut());
function fit() {if(points.length)map.fitBounds(L.latLngBounds(unwrap(points)),{padding:[65,85],maxZoom:16});else farmland.focus();}
$('fit').addEventListener('click',fit);
$('locate').addEventListener('click',()=>{
  if(!navigator.geolocation){notify('Location is unavailable in this browser. Search for a place instead.');return;}
  notify('Finding your location…');
  navigator.geolocation.getCurrentPosition(p=>{map.setView([p.coords.latitude,p.coords.longitude],13);notify('Map centered on your location.');},()=>notify('Location access unavailable. Search for your city instead.'),{timeout:12000});
});
for(const [id,layer,other] of [['satellite',satellite,streets],['streets',streets,satellite]])$(id).addEventListener('click',()=>{
  if(map.hasLayer(layer))return;loadedTiles=failedTiles=0;$('map-error').hidden=true;map.removeLayer(other);layer.addTo(map);
  for(const key of ['satellite','streets']){$(key).classList.toggle('active',key===id);$(key).setAttribute('aria-pressed',String(key===id));}
});
$('dismiss-hint').addEventListener('click',()=>$('map-hint').hidden=true);
$('demo').addEventListener('click',()=>{
  if(drawing)return;
  points=[{lat:33.505,lng:-6.535},{lat:33.507,lng:-6.525},{lat:33.501,lng:-6.520},{lat:33.496,lng:-6.529},{lat:33.499,lng:-6.538}];
  setDrawing(false);save();fit();$('map-hint').hidden=true;notify('An example boundary in Morocco. Drag its vertices to make it yours.');
});

function searchMessage(text) {const div=document.createElement('div');div.className='search-message';div.textContent=text;$('search-results').replaceChildren(div);$('search-results').hidden=false;}
$('search-form').addEventListener('submit',async e=>{
  e.preventDefault();const query=$('search').value.trim();if(!query)return;
  searchController?.abort();searchController=new AbortController();
  const pair=query.match(/^\s*(-?\d+(?:\.\d+)?)\s*[,;]\s*(-?\d+(?:\.\d+)?)\s*$/);
  if(pair){
    const lat=Number(pair[1]),lng=Number(pair[2]);
    if(Math.abs(lat)>85.051129||Math.abs(lng)>180){searchMessage('Use latitude from −85.05 to 85.05 and longitude from −180 to 180.');return;}
    map.setView([lat,lng],12);$('search-results').hidden=true;return;
  }
  searchMessage('Looking for your place…');
  const timeout=setTimeout(()=>searchController.abort(),12000);
  try {
    const response=await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&q=${encodeURIComponent(query)}`,{signal:searchController.signal,headers:{Accept:'application/json'}});
    if(!response.ok)throw new Error('Search unavailable');
    const results=await response.json();
    if(!results.length){searchMessage('No places found. Try a city name or latitude, longitude.');return;}
    $('search-results').replaceChildren();
    results.forEach(result=>{
      const button=document.createElement('button');button.type='button';button.textContent=result.display_name;
      button.addEventListener('click',()=>{
        const box=result.boundingbox?.map(Number);
        if(box?.length===4)map.fitBounds([[box[0],box[2]],[box[1],box[3]]],{padding:[60,65],maxZoom:14});else map.setView([Number(result.lat),Number(result.lon)],12);
        $('search').value=result.display_name.split(',').slice(0,2).join(',');$('search-results').hidden=true;
      });$('search-results').append(button);
    });
    $('search-results').hidden=false;
  } catch {searchMessage('Place search is unavailable. Try coordinates, such as 33.49, -6.50.');}
  finally {clearTimeout(timeout);}
});
document.addEventListener('click',e=>{if(!e.target.closest('.search-wrap'))$('search-results').hidden=true;});
$('help').addEventListener('click',()=>$('help-dialog').showModal());
for(const id of ['close-help','got-it'])$(id).addEventListener('click',()=>$('help-dialog').close());
$('help-dialog').addEventListener('click',e=>{if(e.target===$('help-dialog')){const b=e.target.getBoundingClientRect();if(e.clientX<b.left||e.clientX>b.right||e.clientY<b.top||e.clientY>b.bottom)e.target.close();}});
document.addEventListener('keydown',e=>{
  if(['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)||$('help-dialog').open)return;
  if(e.key==='/'){e.preventDefault();$('search').focus();}
  if(!drawing)return;
  if(e.key==='Enter'){e.preventDefault();finish();}
  if(e.key==='Escape')$('cancel').click();
  if(e.key==='Backspace'||((e.ctrlKey||e.metaKey)&&e.key==='z')){e.preventDefault();$('undo').click();}
});
new ResizeObserver(()=>map.invalidateSize()).observe($('map'));
try {
  const stored=JSON.parse(localStorage.getItem(storageKey));
  if(Array.isArray(stored)&&stored.length<=10000&&validPolygon(stored)){points=stored;setDrawing(false);$('map-hint').hidden=true;}
}catch { /* Start with an empty map when stored data is invalid or unavailable. */ }
render();
