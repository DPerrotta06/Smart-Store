/* Tiny SVG charts for the reports. No library needed, works offline on the kiosk.
   lineChart(box, points, opts)  points = [{label, value}]   (a trend over time)
   barChart(box, items, opts)    items  = [{label, value}]   (a comparison, horizontal bars)
   opts: {money: true} formats values as dollars; {empty: 'text'} when there is nothing to draw. */
(function(){
  const NS = 'http://www.w3.org/2000/svg';
  const fmtVal = (v, o) => o.money ? '$' + Number(v).toFixed(2) : String(Math.round(v * 100) / 100);
  function svg(tag, attrs, text){
    const e = document.createElementNS(NS, tag);
    for(const k in attrs) e.setAttribute(k, attrs[k]);
    if(text !== undefined) e.textContent = text;
    return e;
  }
  function niceMax(v){
    if(v <= 0) return 1;
    const p = Math.pow(10, Math.floor(Math.log10(v))), n = v / p;
    return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
  }
  function emptyMsg(box, o){
    const p = document.createElement('p'); p.className = 'empty'; p.textContent = o.empty || 'Nothing to show for this period.';
    box.replaceChildren(p);
  }

  window.lineChart = function(box, points, o = {}){
    if(!points.length || points.every(p => !p.value) && !o.keepZeros) return emptyMsg(box, o);
    const W = 720, H = 240, L = 56, R = 16, T = 16, B = 40;
    const lo = o.fromZero === false ? Math.min(...points.map(p => p.value)) : 0;
    let hi = Math.max(...points.map(p => p.value));
    const minV = o.fromZero === false ? Math.max(0, lo - (hi - lo || hi * 0.1 || 1) * 0.5) : 0;
    hi = o.fromZero === false ? hi + (hi - lo || hi * 0.1 || 1) * 0.5 : niceMax(hi);
    const x = i => points.length === 1 ? (L + W - R) / 2 : L + i * (W - L - R) / (points.length - 1);
    const y = v => T + (H - T - B) * (1 - (v - minV) / (hi - minV || 1));
    const s = svg('svg', {viewBox: `0 0 ${W} ${H}`, class: 'chart', role: 'img', 'aria-label': o.title || 'Line chart'});
    for(let i = 0; i <= 4; i++){           // grid and y labels
      const v = minV + (hi - minV) * i / 4, yy = y(v);
      s.append(svg('line', {x1: L, x2: W - R, y1: yy, y2: yy, class: 'grid'}));
      s.append(svg('text', {x: L - 8, y: yy + 4, 'text-anchor': 'end', class: 'tick'}, fmtVal(v, o)));
    }
    const every = Math.ceil(points.length / 8);   // at most ~8 x labels
    points.forEach((p, i) => { if(i % every === 0 || i === points.length - 1)
      s.append(svg('text', {x: x(i), y: H - 12, 'text-anchor': 'middle', class: 'tick'}, p.short || p.label)) });
    s.append(svg('polyline', {points: points.map((p, i) => `${x(i)},${y(p.value)}`).join(' '), class: 'line'}));
    points.forEach((p, i) => {
      const dot = svg('circle', {cx: x(i), cy: y(p.value), r: points.length > 40 ? 2.5 : 4, class: 'dot'});
      dot.append(svg('title', {}, `${p.label}: ${fmtVal(p.value, o)}`));
      s.append(dot);
    });
    box.replaceChildren(s);
  };

  window.barChart = function(box, items, o = {}){
    if(!items.length) return emptyMsg(box, o);
    const rowH = 30, W = 720, L = 180, R = 70, H = items.length * rowH + 8;
    const hi = Math.max(...items.map(i => i.value)) || 1;
    const s = svg('svg', {viewBox: `0 0 ${W} ${H}`, class: 'chart', role: 'img', 'aria-label': o.title || 'Bar chart'});
    items.forEach((it, i) => {
      const yy = 4 + i * rowH, w = (W - L - R) * it.value / hi;
      const name = it.label.length > 24 ? it.label.slice(0, 23) + '…' : it.label;
      s.append(svg('text', {x: L - 8, y: yy + 19, 'text-anchor': 'end', class: 'tick'}, name));
      const bar = svg('rect', {x: L, y: yy + 4, width: Math.max(w, it.value ? 2 : 0), height: rowH - 10, rx: 4, class: 'bar' + (it.cls ? ' ' + it.cls : '')});
      bar.append(svg('title', {}, `${it.label}: ${fmtVal(it.value, o)}`));
      s.append(bar);
      s.append(svg('text', {x: L + w + 6, y: yy + 19, class: 'tick'}, fmtVal(it.value, o)));
    });
    box.replaceChildren(s);
  };

  /* shared helpers for the date range pickers */
  window.isoDay = d => { const t = new Date(d); t.setMinutes(t.getMinutes() - t.getTimezoneOffset()); return t.toISOString().slice(0, 10) };
  window.presetRange = name => {
    const today = new Date(), start = new Date(today);
    if(name === 'week') start.setDate(today.getDate() - 6);
    else if(name === 'month') start.setDate(today.getDate() - 29);
    else if(name === 'thismonth') start.setDate(1);
    else if(name === 'year') start.setDate(today.getDate() - 364);
    return [isoDay(start), isoDay(today)];
  };
})();
