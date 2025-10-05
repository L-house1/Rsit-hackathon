const map = L.map('map', { minZoom: 2, maxZoom: 9 }).setView([37.8, -96], 4);
const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution:'© OSM'});
osm.addTo(map); 

const gibs = L.tileLayer(
  'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg',
  { attribution:'© NASA GIBS', tileSize:256, maxZoom:9, noWrap:true });

const baseMaps = { "OpenStreetMap": osm };
const overlayMaps = { "NASA GIBS": gibs };
L.control.layers(baseMaps, overlayMaps).addTo(map);

setTimeout(()=>map.invalidateSize(),0);

const southWest = L.latLng(-90, -180);
const northEast = L.latLng(90, 180);
const bounds = L.latLngBounds(southWest, northEast);
map.setMaxBounds(bounds);
map.on('drag', function() { map.panInsideBounds(bounds, { animate: false }); });

// --- Global State ---
let chart;
let fullData = [];
const selectedAOIs = new Set();
const aoiMarkers = {};

function rsiColor(v){ const t = window.RSIT_THRESHOLDS; return v>=t.alert?'red':(v>=t.warn?'orange':'green'); }

function updateMarkerStyles() {
    Object.entries(aoiMarkers).forEach(([aoiKey, marker]) => {
        const isSelected = selectedAOIs.has(aoiKey);
        marker.setStyle({
            fillOpacity: isSelected ? 0.9 : 0.3,
            opacity: isSelected ? 1 : 0.5
        });
    });
}

function toggleAoiSelection(aoiKey) {
    const checkbox = document.getElementById(`aoi-cb-${aoiKey}`);
    if (selectedAOIs.has(aoiKey)) {
        selectedAOIs.delete(aoiKey);
        if(checkbox) checkbox.checked = false;
    } else {
        selectedAOIs.add(aoiKey);
        if(checkbox) checkbox.checked = true;
    }
    updateMarkerStyles();
    updateRsiPriceChart(); 
}

function createAoiCheckboxes() {
    const container = document.getElementById('aoi-selector');
    if (!container) return;

    const aoiKeys = Object.keys(window.RSIT_AOIS);
    aoiKeys.forEach(aoiKey => {
        selectedAOIs.add(aoiKey); // Select all by default

        const aoiConfig = window.RSIT_AOIS[aoiKey];
        const wrapper = document.createElement('div');
        wrapper.className = 'aoi-checkbox-wrapper';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `aoi-cb-${aoiKey}`;
        checkbox.value = aoiKey;
        checkbox.checked = true;
        checkbox.addEventListener('change', () => toggleAoiSelection(aoiKey));

        const label = document.createElement('label');
        label.htmlFor = `aoi-cb-${aoiKey}`;
        label.textContent = aoiConfig.name || aoiKey;

        wrapper.appendChild(checkbox);
        wrapper.appendChild(label);
        container.appendChild(wrapper);
    });
}

function updateRsiPriceChart() {
    const ctx = document.getElementById('rsiPriceChart').getContext('2d');
    
    if (chart) chart.destroy();

    if (selectedAOIs.size === 0) {
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.save();
        ctx.textAlign = 'center';
        ctx.fillStyle = '#888';
        ctx.font = '16px Arial';
        ctx.fillText('Please select an AOI to display the chart.', ctx.canvas.width / 2, 50);
        ctx.restore();
        return;
    }

    const byAoi = {};
    fullData.forEach(d => {
      byAoi[d.aoi] ??= {};
      byAoi[d.aoi][d.date] = d;
    });

    const allAoiKeys = Object.keys(byAoi);
    const allDates = [...new Set(fullData.map(d => d.date))].sort();

    // Use all dates from the data file directly
    const datesWithAny = allDates;

    const aoiColors = ['#ff4d7a', '#ff9f40', '#ffcd56'];
    const selectedAoiKeys = Array.from(selectedAOIs);

    const rsiDs = selectedAoiKeys.map((a,i)=>({ 
      label:`RSI (${(window.RSIT_AOIS[a]?.name||a)})`,
      data: datesWithAny
        .map(dt => {
          const v = byAoi[a]?.[dt]?.rsi;
          return (v==null) ? null : {x:new Date(dt), y:v, kind:byAoi[a][dt]?.kind||'past'};
        })
        .filter(Boolean),
      yAxisID:'y-rsi', borderColor: aoiColors[i % aoiColors.length], backgroundColor: aoiColors[i % aoiColors.length]+'26', tension:.3,
      segment:{ borderDash: ctx => ctx.p1.raw.kind==='forecast' ? [5,5] : undefined }
    }));

    const priceDs = selectedAoiKeys.map((a,i)=>({ 
      label:`Price (${(window.RSIT_AOIS[a]?.name||a)}) (shift3)`,
      data: datesWithAny
        .map(dt => {
          let v = byAoi[a]?.[dt]?.price_shift3;
          if (v==null) {
            for (const b of allAoiKeys) { const w = byAoi[b]?.[dt]?.price_shift3; if (w!=null) { v=w; break; } }
          }
          return (v==null) ? null : {x:new Date(dt), y:v, kind:byAoi[a]?.[dt]?.kind||'past'};
        })
        .filter(Boolean),
      yAxisID:'y-price', borderColor:`rgba(77,163,255,${1 - i*0.2})`, backgroundColor:`rgba(77,163,255,${0.15 - i*0.03})`, tension:.3,
      segment:{ borderDash: ctx => ctx.p1.raw.kind==='forecast' ? [5,5] : undefined }
    }));

    const datasets = [...rsiDs, ...priceDs];

    const firstForecastDate = datesWithAny.find(d =>
        fullData.some(x => x.date === d && x.kind === 'forecast')
    ) || datesWithAny[datesWithAny.length - 1];

    chart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true, maintainAspectRatio: false, parsing: false, spanGaps: true,
            elements: { point: { radius: 0 } },
            plugins:{
              legend:{position:'top'}, tooltip:{mode:'index',intersect:false}, 
              annotation:{ annotations:{
                forecastBox:{type:'box', xMin:firstForecastDate, xMax:datesWithAny[datesWithAny.length-1], backgroundColor:'rgba(100,100,100,0.08)', borderColor:'rgba(0,0,0,0)'}, 
                warnLine:{type:'line', yMin:window.RSIT_THRESHOLDS.warn, yMax:window.RSIT_THRESHOLDS.warn, yScaleID:'y-rsi', borderColor:'orange', borderWidth:2, borderDash:[5,5], label:{content:'Warn',display:true}}, 
                alertLine:{type:'line', yMin:window.RSIT_THRESHOLDS.alert, yMax:window.RSIT_THRESHOLDS.alert, yScaleID:'y-rsi', borderColor:'red', borderWidth:2, borderDash:[5,5], label:{content:'Alert',display:true}} 
            }}},
            scales:{ 
                x: { type: 'time', time: { unit: 'day' }, min: datesWithAny[0], max: datesWithAny[datesWithAny.length - 1] },
                'y-rsi':{position:'left',min:0,max:1}, 
                'y-price':{position:'right',grid:{drawOnChartArea:false}} 
            }
        }
    });
}

// --- Initial Load ---
createAoiCheckboxes();

const url = (window.RSIT_DATA_FILE || 'data/merged_from_es.json') + '?t=' + Date.now();
fetch(url, { cache: 'no-store' })
  .then(r => r.json())
  .then(arr => {
    if(!Array.isArray(arr) || arr.length===0) throw new Error('No RSI data');
    fullData = arr.sort((a,b)=> (a.date<b.date?-1:1));

    const latestByAoi = fullData.reduce((acc, d) => {
        if(d.kind !== 'forecast') acc[d.aoi] = d;
        return acc;
    }, {});

    Object.keys(window.RSIT_AOIS).forEach(aoiKey => {
        const aoiConfig = window.RSIT_AOIS[aoiKey];
        if (!aoiConfig) return;

        const latest = latestByAoi[aoiKey];
        const v = Number(latest?.rsi || 0);
        const marker = L.circleMarker([aoiConfig.lat, aoiConfig.lon], { 
            radius:8, 
            color: rsiColor(v), 
            fillOpacity:0.9 
        }).addTo(map);
        
        marker.bindPopup(`AOI: ${aoiConfig.name}<br/>Date: ${latest?.date || 'N/A'}<br/>RSI: ${v.toFixed(2)}`);
        marker.on('click', () => toggleAoiSelection(aoiKey));
        aoiMarkers[aoiKey] = marker;
    });

    updateMarkerStyles();
    updateRsiPriceChart();
  })
  .catch(e => {
    console.error(e);
    const chartCtx = document.getElementById('rsiPriceChart').getContext('2d');
    chartCtx.fillText('Chart data failed to load.', chartCtx.canvas.width/2, 50);
    Object.values(window.RSIT_AOIS).forEach(aoi => {
        const m = L.circleMarker([aoi.lat, aoi.lon], { radius:8, color:'gray', fillOpacity:0.5 }).addTo(map);
        m.bindPopup(`RSI data unavailable for ${aoi.name}`);
    });
  });

setInterval(()=>location.reload(), 60000);