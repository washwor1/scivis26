// globe.js

(async () => {
    const globe = Globe()(document.getElementById('globeViz'))
        .globeImageUrl('/api/global_heatmap.png?date=1950-01-01')
        .width(window.innerWidth)
        .height(window.innerHeight)
        .enablePointerInteraction(true);

    // 2) Build a tooltip DIV (hidden by default)
    const tooltip = document.createElement('div');
    Object.assign(tooltip.style, {
        position: 'fixed',
        background: 'rgba(0,0,0,0.8)',
        color: 'white',
        padding: '6px 10px',
        borderRadius: '4px',
        fontSize: '13px',
        pointerEvents: 'none',
        display: 'none',
        opacity: 0,
        transition: 'opacity 0.2s',
        zIndex: 1000,
        whiteSpace: 'nowrap'
    });
    document.body.appendChild(tooltip);

    let hoveredFeature = null;

    // 3) Once the globe is initialized, fetch and draw the country polygons
    globe.onGlobeReady(async () => {
        const resp = await fetch('/api/countries');
        const geojson = await resp.json();
        const features = geojson.features;

        globe
            .polygonsData(features)
            .polygonAltitude(f => f === hoveredFeature ? 0.03 : 0.015)
            .polygonCapCurvatureResolution(30)
            .polygonCapColor(f => f === hoveredFeature
                ? 'rgba(255, 200, 0, 0.4)'
                : 'rgba(0, 0, 0, 0.1)')
            .polygonSideColor('rgba(0, 0, 0, 0)')
            .polygonStrokeColor(f => f === hoveredFeature
                ? '#ff6600'
                : 'rgba(255, 204, 0, 0.6)')
            .onPolygonHover(feature => {
                hoveredFeature = feature;
                if (feature) {
                    tooltip.textContent = feature.properties.ADMIN
                        || feature.properties.name
                        || 'Unknown';
                    tooltip.style.display = 'block';
                    tooltip.style.opacity = 1;
                } else {
                    tooltip.style.opacity = 0;
                    setTimeout(() => tooltip.style.display = 'none', 200);
                }
                // trigger a redraw so altitude & colors update:
                globe.polygonsData(features);
            })
            .onPolygonClick(feature => {
                if (!feature) return;
                // center on the clicked country
                const centroid = feature.properties.centroid
                    || d3.geoCentroid(feature);
                globe.pointOfView(
                    { lat: centroid[1], lng: centroid[0], altitude: 1.5 },
                    1000
                );
            });
        // --- Helper to build URL from controls ---
        function makeUrl() {
            const date = document.getElementById('datePicker').value;
            const variable = document.getElementById('variablePicker').value;
            const model = document.getElementById('modelPicker').value;
            const scenario = document.getElementById('scenarioPicker').value;
            return `/api/global_heatmap.png`
                + `?date=${encodeURIComponent(date)}`
                + `&variable=${encodeURIComponent(variable)}`
                + `&model=${encodeURIComponent(model)}`
                + `&scenario=${encodeURIComponent(scenario)}`;
        }

        // --- Update globe texture whenever pickers change ---
        ['datePicker', 'variablePicker', 'modelPicker', 'scenarioPicker'].forEach(id => {
            document.getElementById(id).addEventListener('change', () => {
                globe.globeImageUrl(makeUrl());
            });
        });

        let playYearsActive = false;
        let playDaysActive = false;

        // Parse/format helpers (unchanged)
        function parseDate(str) {
            const [y, m, d] = str.split('-').map(s => parseInt(s, 10));
            return new Date(y, m - 1, d);
        }
        function formatDate(dt) {
            const mm = String(dt.getMonth() + 1).padStart(2, '0');
            const dd = String(dt.getDate()).padStart(2, '0');
            return `${dt.getFullYear()}-${mm}-${dd}`;
        }

        // Returns a promise that resolves once the URL’s image is loaded (or on error)
        function preloadImage(url) {
            return new Promise(resolve => {
                const img = new Image();
                img.crossOrigin = 'anonymous';
                img.onload = () => resolve(true);
                img.onerror = () => resolve(false);
                img.src = url;
            });
        }

        // Async runner for years
        async function runPlayYears() {
            const picker = document.getElementById('datePicker');
            const max = parseDate(picker.max);
            const btn = document.getElementById('playYears');

            while (playYearsActive) {
                let dt = parseDate(picker.value);
                dt.setFullYear(dt.getFullYear() + 1);
                if (dt > max) break;
                picker.value = formatDate(dt);

                const url = makeUrl();
                await preloadImage(url);         // wait for the PNG to load
                globe.globeImageUrl(url);        // then update the globe
            }

            playYearsActive = false;
            btn.textContent = '▶ Play Years';
        }

        // Async runner for days
        async function runPlayDays() {
            const picker = document.getElementById('datePicker');
            const max = parseDate(picker.max);
            const btn = document.getElementById('playDays');

            while (playDaysActive) {
                let dt = parseDate(picker.value);
                dt.setDate(dt.getDate() + 1);
                if (dt > max) break;
                picker.value = formatDate(dt);

                const url = makeUrl();
                await preloadImage(url);         // wait for the PNG to load
                globe.globeImageUrl(url);        // then update the globe
            }

            playDaysActive = false;
            btn.textContent = '▶ Play Days';
        }

        // Wire up the buttons
        document.getElementById('playYears').addEventListener('click', () => {
            playYearsActive = !playYearsActive;
            const btn = document.getElementById('playYears');
            if (playYearsActive) {
                btn.textContent = '⏸ Pause Years';
                runPlayYears();
            } else {
                btn.textContent = '▶ Play Years';
            }
        });

        document.getElementById('playDays').addEventListener('click', () => {
            playDaysActive = !playDaysActive;
            const btn = document.getElementById('playDays');
            if (playDaysActive) {
                btn.textContent = '⏸ Pause Days';
                runPlayDays();
            } else {
                btn.textContent = '▶ Play Days';
            }
        });
        document.getElementById('computeTop').addEventListener('click', async () => {
            // 1) Read control values
            const start = document.getElementById('startDatePicker').value;
            const end = document.getElementById('endDatePicker').value;
            const variable = document.getElementById('variablePicker').value;
            const model = document.getElementById('modelPicker').value;
            const scenario = document.getElementById('scenarioPicker').value;

            // 2) Build the API URL
            const url = `/api/top_changes`
                + `?metric=${encodeURIComponent(variable)}`
                + `&model=${encodeURIComponent(model)}`
                + `&scenario=${encodeURIComponent(scenario)}`
                + `&start_date=${encodeURIComponent(start)}`
                + `&end_date=${encodeURIComponent(end)}`
                + `&quality=0`
                + `&top_n=5`;

            // 3) Fetch top‑5 results
            const resp = await fetch(url);
            const top5 = await resp.json();

            // 4) Locate and clear the container
            const container = document.getElementById('topList');
            container.innerHTML = '';

            // 5) Add title
            const title = document.createElement('h3');
            title.textContent = `Climate Change Hotspots ${start} – ${end}`;
            container.appendChild(title);

            // 6) Build the table
            const table = document.createElement('table');
            table.style.borderCollapse = 'collapse';
            table.style.marginTop = '8px';

            // 6a) Header row
            const header = table.insertRow();
            ['Country', 'Δ T (°C)', 'Damage (% GDP)'].forEach(txt => {
                const th = document.createElement('th');
                th.textContent = txt;
                th.style.padding = '4px 8px';
                th.style.borderBottom = '2px solid #333';
                th.style.textAlign = 'left';
                header.appendChild(th);
            });

            // 6b) Data rows
            top5.forEach(item => {
                const row = table.insertRow();

                // Country cell
                let cell = row.insertCell();
                cell.textContent = item.country;
                cell.style.padding = '4px 8px';

                // ΔT cell
                cell = row.insertCell();
                cell.textContent = item.change.toFixed(2);
                cell.style.padding = '4px 8px';
                cell.style.textAlign = 'right';

                // Damage % cell
                cell = row.insertCell();
                cell.textContent = (item.damage * 100).toFixed(2);
                cell.style.padding = '4px 8px';
                cell.style.textAlign = 'right';
            });

            // 7) Append table to the container
            container.appendChild(table);
        });

        // 4) Move the tooltip with the mouse
        const canvas = globe.renderer().domElement;
        canvas.addEventListener('mousemove', e => {
            tooltip.style.left = `${e.clientX + 12}px`;
            tooltip.style.top = `${e.clientY - 28}px`;
        });
    });

    // 5) Handle window resizes
    window.addEventListener('resize', () => {
        globe.width(window.innerWidth).height(window.innerHeight);
    });
})();
