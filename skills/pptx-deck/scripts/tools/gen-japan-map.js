'use strict';
// 日本全国の都道府県の輪郭を、図解の見本(design/diagrams.html の地図)用の簡略な多角形に変換する。
//
// 使い方: node scripts/tools/gen-japan-map.js <ne_10m_admin_1_states_provinces.geojson> [出力 JSON]
// 出典: Natural Earth（パブリックドメイン。https://www.naturalearthdata.com/about/terms-of-use/ ）
//   admin-1 の 10m、日本の 47 都道府県。https://github.com/nvkelso/natural-earth-vector から取得する
// 出力 design/japan-map.json: { meta, prefs: [{ name, rings: [[[x, y], …], …], centroid: [x, y] }] }
//   座標は px(1280x720 のスライド上の寸法)。本土・北海道は左上を原点にした枠に、沖縄は左上の沖合に挿入する
const fs = require('node:fs');
const path = require('node:path');

const SRC = process.argv[2];
const OUT = process.argv[3] || path.join(__dirname, '..', '..', 'design', 'japan-map.json');
if (!SRC) {
  console.error('使い方: node scripts/tools/gen-japan-map.js <ne_10m_admin_1_states_provinces.geojson> [出力 JSON]');
  process.exit(1);
}

const MAP_H = 430; // 北海道の北端から九州の南端までの高さ(px)
const TOL = 0.7; // 簡略化の許容誤差(px)
const MIN_AREA = 0.03; // これ未満の島は捨てる(平方度)。沖縄本島は小さいので、挿入では拡大して描く
const MIN_AREA_OKINAWA = 0.03;
const INSET_SCALE = 2.6; // 沖縄の挿入は、本土の縮尺の 2.6 倍で描く(そのままだと小さすぎて見えない)

const data = JSON.parse(fs.readFileSync(SRC, 'utf8'));
const feats = data.features.filter((f) => f.properties.iso_a2 === 'JP' || f.properties.admin === 'Japan');
if (feats.length !== 47) throw new Error(`日本の都道府県が 47 件でない: ${feats.length}`);

const shortName = (ja) => (ja === '北海道' ? ja : ja.replace(/[都府県]$/, ''));
const ringArea = (r) => Math.abs(r.reduce((a, p, i) => { const q = r[(i + 1) % r.length]; return a + (p[0] * q[1] - q[0] * p[1]); }, 0)) / 2;
const centroidOf = (r) => {
  let a = 0; let cx = 0; let cy = 0;
  r.forEach((p, i) => { const q = r[(i + 1) % r.length]; const k = p[0] * q[1] - q[0] * p[1]; a += k; cx += (p[0] + q[0]) * k; cy += (p[1] + q[1]) * k; });
  return a === 0 ? r[0] : [cx / (3 * a), cy / (3 * a)];
};

// Douglas-Peucker(閉じた輪郭は、最も離れた 2 点で分けて処理する)
function simplify(pts, tol) {
  const dp = (a, b) => {
    const out = [];
    let idx = -1; let dmax = 0;
    const [x1, y1] = pts[a]; const [x2, y2] = pts[b];
    const dx = x2 - x1; const dy = y2 - y1; const len = Math.hypot(dx, dy) || 1e-9;
    for (let i = a + 1; i < b; i++) {
      const d = Math.abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / len;
      if (d > dmax) { dmax = d; idx = i; }
    }
    if (dmax > tol) { out.push(...dp(a, idx), pts[idx], ...dp(idx, b)); }
    return out;
  };
  const open = pts.slice(0, -1); // 末尾は始点と同じ点
  if (open.length < 4) return open;
  let far = 1; let best = 0;
  open.forEach((p, i) => { const d = Math.hypot(p[0] - open[0][0], p[1] - open[0][1]); if (d > best) { best = d; far = i; } });
  const loop = open.concat([open[0]]);
  const first = (() => { const sub = open.slice(0, far + 1); const t = sub.concat([]); pts = t; return [open[0], ...dp(0, t.length - 1), open[far]]; })();
  const second = (() => { const sub = open.slice(far).concat([open[0]]); pts = sub; return [...dp(0, sub.length - 1)]; })();
  void loop;
  return first.concat(second);
}

// 1 回目: 経緯度 → 平面(経度は cos(37°) で縮める)。本土の範囲を求める
const COS = Math.cos((37 * Math.PI) / 180);
const proj = ([lon, lat]) => [lon * COS, -lat];
const polys = [];
for (const f of feats) {
  const ja = f.properties.name_ja;
  const name = shortName(ja);
  const geom = f.geometry;
  const parts = geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates;
  for (const poly of parts) {
    const ring = poly[0]; // 外周だけ(穴は使わない)
    const ll = ring;
    const area = ringArea(ll);
    const [clon, clat] = centroidOf(ll);
    const okinawa = name === '沖縄';
    if (area < (okinawa ? MIN_AREA_OKINAWA : MIN_AREA)) continue;
    if (!okinawa && clat < 30.9) continue; // 屋久島・種子島・奄美などは捨てる
    if (okinawa && clon > 129) continue; // 大東諸島などの離島は捨て、沖縄本島だけにする
    polys.push({ name, okinawa, ring: ring.map(proj), clon, clat });
  }
}
const main = polys.filter((p) => !p.okinawa);
const xs = main.flatMap((p) => p.ring.map((q) => q[0]));
const ys = main.flatMap((p) => p.ring.map((q) => q[1]));
const x0 = Math.min(...xs); const y0 = Math.min(...ys);
const scale = MAP_H / (Math.max(...ys) - y0);
const toPx = (p) => [(p[0] - x0) * scale, (p[1] - y0) * scale];
const W = Math.ceil((Math.max(...xs) - x0) * scale);

// 沖縄は、左上の沖合(日本海側の空き)に、同じ縮尺で挿入する
const oki = polys.filter((p) => p.okinawa);
const ox = oki.flatMap((p) => p.ring.map((q) => q[0]));
const oy = oki.flatMap((p) => p.ring.map((q) => q[1]));
const okiOrigin = [Math.min(...ox), Math.min(...oy)];
const INSET = { x: 30, y: 44 }; // 沖縄の左上を置く位置(枠の内側)
const toInset = (p) => [(p[0] - okiOrigin[0]) * scale * INSET_SCALE + INSET.x, (p[1] - okiOrigin[1]) * scale * INSET_SCALE + INSET.y];

const r1 = (n) => Math.round(n * 10) / 10;
const prefs = {};
for (const p of polys) {
  const px = p.ring.map(p.okinawa ? toInset : toPx);
  const simp = simplify(px, TOL).map((q) => [r1(q[0]), r1(q[1])]);
  if (simp.length < 3) continue;
  (prefs[p.name] ||= { name: p.name, rings: [], areaMax: 0, centroid: null });
  prefs[p.name].rings.push(simp);
  const a = ringArea(simp);
  if (a > prefs[p.name].areaMax) { prefs[p.name].areaMax = a; prefs[p.name].centroid = centroidOf(simp).map(r1); }
}
const list = Object.values(prefs).map(({ name, rings, centroid }) => ({ name, rings, centroid }));
if (list.length !== 47) throw new Error(`47 都道府県にならない: ${list.length}`);
const points = list.reduce((a, p) => a + p.rings.reduce((b, r) => b + r.length, 0), 0);
const okiBox = (() => { const px = oki.flatMap((p) => p.ring.map(toInset)); return [Math.min(...px.map((q) => q[0])), Math.min(...px.map((q) => q[1])), Math.max(...px.map((q) => q[0])), Math.max(...px.map((q) => q[1]))].map(r1); })();
const out = {
  meta: {
    source: 'Natural Earth admin-1 (10m), public domain',
    url: 'https://www.naturalearthdata.com/',
    size: [W, MAP_H],
    okinawaBox: okiBox,
    tolerancePx: TOL,
    insetScale: INSET_SCALE,
    points,
  },
  prefs: list,
};
fs.writeFileSync(OUT, JSON.stringify(out));
console.log(JSON.stringify({ ok: true, out: OUT, prefs: list.length, points, size: [W, MAP_H], okinawaBox: okiBox }));
