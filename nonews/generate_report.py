"""
generate_report.py — Generates HTML dashboard reports from DB data.

Objectives:
    Build HTML dashboard reports using data from report.py. Multiple template
    variants were created during design exploration. D3 is the final accepted
    design and the default output of `py -m nonews report`.

Templates:
    - A: Dark theme, data-first dashboard (exploration)
    - B: Light editorial/newspaper style (exploration)
    - C: Light analytics grid with dense charts (exploration)
    - D: Editorial with hierarchical treemap (exploration, based on B)
    - D1: Editorial with drill-down navigation + date filter (exploration)
    - D2: Editorial with accordion hierarchy + real-time date slider (exploration)
    - D3: Editorial with sidebar tree nav + date filter + muted palette (FINAL)

    D3 features:
    - Fixed left sidebar with collapsible tree: Nacional/Internacional → Region → Articles
    - Date range filter in sidebar with "Filtrar" button
    - Reactive charts (sentiment pie, region bar, timeline) that update with filters
    - Article cards grid → detail view on click
    - Muted color palette: sage green (#588157), dusty brick (#bc4749),
      soft gray (#b5b5b5), steel blue (#457b9d)

Usage:
    py -m nonews report                        # generates D3 → data/report.html
    py -m nonews report -o custom.html         # custom output path
    py -m nonews.generate_report               # generates D3 (default)
    py -m nonews.generate_report --template A  # generates a specific template
    py -m nonews.generate_report --template all # generates all templates

Connections:
    - report.py: provides build_report_data(), build_hierarchy_data(),
      build_sidebar_data(), build_hierarchy_articles_data().
    - cli.py: calls generate("D3") from the `report` command.
    - Writes output to data/report.html (D3 default) or data/report_<template>.html.
"""

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

from nonews.report import build_report_data

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _inject_data(html: str, data: dict) -> str:
    """Replace the __DATA__ placeholder with actual JSON data."""
    return html.replace("__DATA__", json.dumps(data, ensure_ascii=False))


# ──────────────────────────────────────────────────────────────
# PROPOSAL A — Dark theme, data-first dashboard
# ──────────────────────────────────────────────────────────────
TEMPLATE_A = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>nonews — Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0f1117; color: #e1e4e8; font-family: 'Segoe UI', system-ui, sans-serif; padding: 24px; }
h1 { font-size: 28px; font-weight: 600; margin-bottom: 8px; color: #fff; }
.subtitle { color: #8b949e; font-size: 14px; margin-bottom: 32px; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }
.stat-card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; text-align: center; }
.stat-card .value { font-size: 36px; font-weight: 700; }
.stat-card .label { font-size: 13px; color: #8b949e; margin-top: 4px; }
.stat-card.positive .value { color: #3fb950; }
.stat-card.negative .value { color: #f85149; }
.stat-card.neutral .value { color: #8b949e; }
.stat-card.total .value { color: #58a6ff; }
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px; }
.chart-card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 24px; }
.chart-card h3 { font-size: 16px; margin-bottom: 16px; color: #c9d1d9; }
.chart-card canvas { max-height: 280px; }
.articles-section { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 24px; margin-bottom: 32px; }
.articles-section h3 { font-size: 16px; margin-bottom: 16px; color: #c9d1d9; }
.article-item { display: flex; align-items: center; padding: 12px 0; border-bottom: 1px solid #21262d; gap: 12px; }
.article-item:last-child { border-bottom: none; }
.badge { padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
.badge.positive { background: #0d3320; color: #3fb950; }
.badge.negative { background: #3d1214; color: #f85149; }
.badge.neutral { background: #1c2128; color: #8b949e; }
.article-title { flex: 1; font-size: 14px; color: #c9d1d9; }
.article-region { font-size: 12px; color: #8b949e; }
.article-date { font-size: 12px; color: #484f58; }
.footer { text-align: center; color: #484f58; font-size: 12px; padding-top: 16px; }
</style>
</head>
<body>
<h1>nonews Dashboard</h1>
<p class="subtitle">Resumen del panorama informativo de Mexico</p>

<div class="stats-row">
  <div class="stat-card total"><div class="value" id="total">-</div><div class="label">Articulos totales</div></div>
  <div class="stat-card positive"><div class="value" id="pos-pct">-</div><div class="label">Positivos</div></div>
  <div class="stat-card negative"><div class="value" id="neg-pct">-</div><div class="label">Negativos</div></div>
  <div class="stat-card neutral"><div class="value" id="neu-pct">-</div><div class="label">Neutrales</div></div>
</div>

<div class="charts-grid">
  <div class="chart-card"><h3>Distribucion de sentimiento</h3><canvas id="sentimentChart"></canvas></div>
  <div class="chart-card"><h3>Cobertura por region (top 15)</h3><canvas id="regionChart"></canvas></div>
  <div class="chart-card"><h3>Articulos por dia (ultimos 30)</h3><canvas id="timelineChart"></canvas></div>
  <div class="chart-card"><h3>Sentimiento por region (top 12)</h3><canvas id="sentRegionChart"></canvas></div>
</div>

<div class="articles-section">
  <h3>Articulos mas recientes</h3>
  <div id="articlesList"></div>
</div>

<p class="footer">Generado el <span id="genDate"></span> — nonews</p>

<script>
const DATA = __DATA__;

document.getElementById('total').textContent = DATA.summary.total;
document.getElementById('pos-pct').textContent = DATA.summary.positive_pct + '%';
document.getElementById('neg-pct').textContent = DATA.summary.negative_pct + '%';
document.getElementById('neu-pct').textContent = DATA.summary.neutral_pct + '%';
document.getElementById('genDate').textContent = DATA.summary.generated_at;

new Chart(document.getElementById('sentimentChart'), {
  type: 'doughnut',
  data: {
    labels: DATA.sentiment.labels,
    datasets: [{ data: DATA.sentiment.values, backgroundColor: ['#3fb950','#f85149','#8b949e'] }]
  },
  options: { plugins: { legend: { position: 'bottom', labels: { color: '#8b949e' } } } }
});

new Chart(document.getElementById('regionChart'), {
  type: 'bar',
  data: {
    labels: DATA.region.labels,
    datasets: [{ data: DATA.region.values, backgroundColor: '#58a6ff' }]
  },
  options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } }, y: { ticks: { color: '#c9d1d9' }, grid: { display: false } } } }
});

new Chart(document.getElementById('timelineChart'), {
  type: 'line',
  data: {
    labels: DATA.timeline.labels.map(d => d.slice(5)),
    datasets: [{ data: DATA.timeline.values, borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.1)', fill: true, tension: 0.3 }]
  },
  options: { plugins: { legend: { display: false } }, scales: { x: { ticks: { color: '#8b949e', maxTicksLimit: 10 }, grid: { color: '#21262d' } }, y: { ticks: { color: '#8b949e' }, grid: { color: '#21262d' } } } }
});

new Chart(document.getElementById('sentRegionChart'), {
  type: 'bar',
  data: {
    labels: DATA.sentiment_region.labels,
    datasets: [
      { label: 'Positivo', data: DATA.sentiment_region.positive, backgroundColor: '#3fb950' },
      { label: 'Negativo', data: DATA.sentiment_region.negative, backgroundColor: '#f85149' },
      { label: 'Neutral', data: DATA.sentiment_region.neutral, backgroundColor: '#484f58' },
    ]
  },
  options: { plugins: { legend: { labels: { color: '#8b949e' } } }, scales: { x: { stacked: true, ticks: { color: '#c9d1d9' }, grid: { display: false } }, y: { stacked: true, ticks: { color: '#8b949e' }, grid: { color: '#21262d' } } } }
});

const list = document.getElementById('articlesList');
DATA.top_articles.forEach(a => {
  const div = document.createElement('div');
  div.className = 'article-item';
  div.innerHTML = '<span class="badge ' + a.sentiment + '">' + a.sentiment + '</span><span class="article-title">' + a.title + '</span><span class="article-region">' + a.region + '</span><span class="article-date">' + a.date + '</span>';
  list.appendChild(div);
});
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────
# PROPOSAL B — Light editorial / newspaper style
# ──────────────────────────────────────────────────────────────
TEMPLATE_B = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>nonews — Resumen Informativo</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #fafaf8; color: #1a1a1a; font-family: Georgia, 'Times New Roman', serif; }
.header { background: #fff; border-bottom: 3px double #1a1a1a; padding: 32px 48px 16px; text-align: center; }
.header h1 { font-size: 42px; font-weight: 900; letter-spacing: -1px; }
.header .tagline { font-size: 14px; color: #666; font-style: italic; margin-top: 4px; }
.header .date { font-size: 13px; color: #999; margin-top: 8px; font-family: system-ui, sans-serif; }
.container { max-width: 1100px; margin: 0 auto; padding: 32px 48px; }
.hero { background: #fff; border: 1px solid #e0e0e0; padding: 32px; margin-bottom: 32px; border-radius: 4px; }
.hero h2 { font-size: 28px; line-height: 1.3; margin-bottom: 12px; }
.hero p { font-size: 16px; line-height: 1.6; color: #444; }
.section-title { font-size: 20px; font-weight: 700; border-bottom: 2px solid #1a1a1a; padding-bottom: 8px; margin: 32px 0 16px; font-family: system-ui, sans-serif; text-transform: uppercase; font-size: 14px; letter-spacing: 1px; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; margin-bottom: 32px; }
.card { background: #fff; border: 1px solid #e0e0e0; border-radius: 4px; padding: 24px; }
.card h3 { font-family: system-ui, sans-serif; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #666; margin-bottom: 16px; }
.card canvas { max-height: 250px; }
.news-list { list-style: none; }
.news-item { padding: 16px 0; border-bottom: 1px solid #eee; display: grid; grid-template-columns: 80px 1fr; gap: 16px; align-items: start; }
.news-item:last-child { border-bottom: none; }
.news-sentiment { font-family: system-ui, sans-serif; font-size: 11px; font-weight: 700; text-transform: uppercase; padding: 4px 8px; border-radius: 3px; text-align: center; }
.news-sentiment.positive { background: #e6f4ea; color: #1e7e34; }
.news-sentiment.negative { background: #fce8e6; color: #c62828; }
.news-sentiment.neutral { background: #f1f3f4; color: #666; }
.news-title { font-size: 16px; line-height: 1.4; }
.news-meta { font-family: system-ui, sans-serif; font-size: 12px; color: #999; margin-top: 4px; }
.summary-bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin: 16px 0; }
.summary-bar .pos { background: #34a853; }
.summary-bar .neg { background: #ea4335; }
.summary-bar .neu { background: #dadce0; }
.summary-text { font-family: system-ui, sans-serif; font-size: 13px; color: #666; display: flex; justify-content: space-between; }
.footer { text-align: center; padding: 24px; color: #999; font-size: 12px; font-family: system-ui, sans-serif; border-top: 1px solid #eee; margin-top: 32px; }
</style>
</head>
<body>

<div class="header">
  <h1>nonews</h1>
  <div class="tagline">Resumen del panorama informativo de Mexico</div>
  <div class="date" id="genDate"></div>
</div>

<div class="container">
  <div class="hero">
    <h2 id="heroTitle">Panorama general</h2>
    <p id="heroText"></p>
    <div class="summary-bar"><div class="pos" id="barPos"></div><div class="neg" id="barNeg"></div><div class="neu" id="barNeu"></div></div>
    <div class="summary-text"><span id="posLabel"></span><span id="negLabel"></span><span id="neuLabel"></span></div>
  </div>

  <div class="two-col">
    <div class="card"><h3>Sentimiento general</h3><canvas id="sentimentChart"></canvas></div>
    <div class="card"><h3>Regiones con mas cobertura</h3><canvas id="regionChart"></canvas></div>
  </div>

  <div class="section-title">Noticias recientes</div>
  <ul class="news-list" id="newsList"></ul>

  <div class="two-col" style="margin-top:32px">
    <div class="card"><h3>Volumen diario</h3><canvas id="timelineChart"></canvas></div>
    <div class="card"><h3>Por categoria</h3><canvas id="categoryChart"></canvas></div>
  </div>
</div>

<div class="footer">Generado el <span id="genDate2"></span> — nonews</div>

<script>
const DATA = __DATA__;

document.getElementById('genDate').textContent = DATA.summary.generated_at;
document.getElementById('genDate2').textContent = DATA.summary.generated_at;

const s = DATA.summary;
document.getElementById('heroTitle').textContent = s.total + ' articulos analizados';
const dominant = s.positive_pct >= s.negative_pct ? 'positivo' : 'negativo';
document.getElementById('heroText').textContent =
  'El ' + Math.max(s.positive_pct, s.negative_pct) + '% de las noticias tiene un tono ' + dominant +
  '. Se cubren ' + s.regions_count + ' regiones distintas del pais.';

document.getElementById('barPos').style.width = s.positive_pct + '%';
document.getElementById('barNeg').style.width = s.negative_pct + '%';
document.getElementById('barNeu').style.width = s.neutral_pct + '%';
document.getElementById('posLabel').textContent = s.positive_pct + '% positivo';
document.getElementById('negLabel').textContent = s.negative_pct + '% negativo';
document.getElementById('neuLabel').textContent = s.neutral_pct + '% neutral';

new Chart(document.getElementById('sentimentChart'), {
  type: 'pie',
  data: { labels: DATA.sentiment.labels, datasets: [{ data: DATA.sentiment.values, backgroundColor: ['#34a853','#ea4335','#dadce0'] }] },
  options: { plugins: { legend: { position: 'bottom' } } }
});

new Chart(document.getElementById('regionChart'), {
  type: 'bar',
  data: { labels: DATA.region.labels, datasets: [{ data: DATA.region.values, backgroundColor: '#4285f4' }] },
  options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { grid: { display: false } } } }
});

new Chart(document.getElementById('timelineChart'), {
  type: 'bar',
  data: { labels: DATA.timeline.labels.map(d => d.slice(5)), datasets: [{ data: DATA.timeline.values, backgroundColor: '#4285f4' }] },
  options: { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } }, y: { grid: { color: '#eee' } } } }
});

new Chart(document.getElementById('categoryChart'), {
  type: 'doughnut',
  data: { labels: DATA.category.labels, datasets: [{ data: DATA.category.values, backgroundColor: ['#4285f4','#ea4335','#fbbc04','#34a853','#ff6d01','#46bdc6','#7b61ff','#e8710a','#1a73e8','#d93025','#f9ab00','#1e8e3e','#e52592','#12b5cb'] }] },
  options: { plugins: { legend: { position: 'right', labels: { font: { size: 11 } } } } }
});

const list = document.getElementById('newsList');
DATA.top_articles.forEach(a => {
  const li = document.createElement('li');
  li.className = 'news-item';
  li.innerHTML = '<span class="news-sentiment ' + a.sentiment + '">' + a.sentiment + '</span><div><div class="news-title">' + a.title + '</div><div class="news-meta">' + a.region + ' — ' + a.date + '</div></div>';
  list.appendChild(li);
});
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────
# PROPOSAL C — Light analytics grid, dense charts
# ──────────────────────────────────────────────────────────────
TEMPLATE_C = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>nonews — Analytics</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #f0f2f5; color: #1d1d1f; font-family: -apple-system, 'Segoe UI', system-ui, sans-serif; padding: 20px; }
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.top-bar h1 { font-size: 22px; font-weight: 700; }
.top-bar .meta { font-size: 13px; color: #86868b; }
.kpi-row { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-bottom: 20px; }
.kpi { background: #fff; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.kpi .num { font-size: 28px; font-weight: 700; }
.kpi .lbl { font-size: 11px; color: #86868b; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
.kpi.pos .num { color: #34c759; }
.kpi.neg .num { color: #ff3b30; }
.kpi.neu .num { color: #8e8e93; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }
.grid-2 { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 20px; }
.panel { background: #fff; border-radius: 10px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.panel h3 { font-size: 13px; font-weight: 600; color: #1d1d1f; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
.panel canvas { max-height: 220px; }
.table-panel { max-height: 400px; overflow-y: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 8px; border-bottom: 2px solid #e5e5ea; font-weight: 600; color: #86868b; font-size: 11px; text-transform: uppercase; position: sticky; top: 0; background: #fff; }
td { padding: 8px; border-bottom: 1px solid #f2f2f7; }
tr:hover { background: #f9f9f9; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.tag.pos { background: #e8f8ed; color: #34c759; }
.tag.neg { background: #ffe5e3; color: #ff3b30; }
.tag.neu { background: #f2f2f7; color: #8e8e93; }
.opinion-text { font-size: 12px; color: #636366; max-width: 300px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.footer { text-align: center; color: #86868b; font-size: 11px; padding: 16px; }
</style>
</head>
<body>

<div class="top-bar">
  <h1>nonews Analytics</h1>
  <div class="meta" id="genDate"></div>
</div>

<div class="kpi-row">
  <div class="kpi"><div class="num" id="kpiTotal">-</div><div class="lbl">Total</div></div>
  <div class="kpi pos"><div class="num" id="kpiPos">-</div><div class="lbl">Positivos</div></div>
  <div class="kpi neg"><div class="num" id="kpiNeg">-</div><div class="lbl">Negativos</div></div>
  <div class="kpi neu"><div class="num" id="kpiNeu">-</div><div class="lbl">Neutrales</div></div>
  <div class="kpi"><div class="num" id="kpiRegions">-</div><div class="lbl">Regiones</div></div>
  <div class="kpi"><div class="num" id="kpiCats">-</div><div class="lbl">Categorias</div></div>
</div>

<div class="grid">
  <div class="panel"><h3>Sentimiento</h3><canvas id="sentChart"></canvas></div>
  <div class="panel"><h3>Top regiones</h3><canvas id="regChart"></canvas></div>
  <div class="panel"><h3>Categorias</h3><canvas id="catChart"></canvas></div>
</div>

<div class="grid-2">
  <div class="panel table-panel">
    <h3>Articulos recientes</h3>
    <table><thead><tr><th>Sent.</th><th>Titulo</th><th>Region</th><th>Opinion</th><th>Fecha</th></tr></thead><tbody id="artTable"></tbody></table>
  </div>
  <div class="panel"><h3>Sentimiento por region</h3><canvas id="sentRegChart"></canvas></div>
</div>

<div class="panel" style="margin-bottom:20px"><h3>Volumen diario (ultimos 30 dias)</h3><canvas id="tlChart" style="max-height:160px"></canvas></div>

<div class="footer">Generado el <span id="genDate2"></span> — nonews</div>

<script>
const D = __DATA__;

document.getElementById('genDate').textContent = D.summary.generated_at;
document.getElementById('genDate2').textContent = D.summary.generated_at;
document.getElementById('kpiTotal').textContent = D.summary.total;
document.getElementById('kpiPos').textContent = D.summary.positive_pct + '%';
document.getElementById('kpiNeg').textContent = D.summary.negative_pct + '%';
document.getElementById('kpiNeu').textContent = D.summary.neutral_pct + '%';
document.getElementById('kpiRegions').textContent = D.summary.regions_count;
document.getElementById('kpiCats').textContent = D.category.labels.length;

const COLORS = { pos: '#34c759', neg: '#ff3b30', neu: '#8e8e93' };

new Chart(document.getElementById('sentChart'), {
  type: 'doughnut',
  data: { labels: D.sentiment.labels, datasets: [{ data: D.sentiment.values, backgroundColor: [COLORS.pos, COLORS.neg, COLORS.neu], borderWidth: 0 }] },
  options: { cutout: '65%', plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } } }
});

new Chart(document.getElementById('regChart'), {
  type: 'bar',
  data: { labels: D.region.labels, datasets: [{ data: D.region.values, backgroundColor: '#007aff', borderRadius: 4 }] },
  options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { grid: { display: false }, ticks: { font: { size: 11 } } } } }
});

new Chart(document.getElementById('catChart'), {
  type: 'polarArea',
  data: { labels: D.category.labels, datasets: [{ data: D.category.values, backgroundColor: ['#007aff','#ff3b30','#ff9500','#34c759','#af52de','#5ac8fa','#ff2d55','#5856d6','#ffcc00','#30b0c7','#ff6482','#64d2ff','#bf5af2','#acd7fa'] }] },
  options: { plugins: { legend: { position: 'right', labels: { font: { size: 10 } } } }, scales: { r: { display: false } } }
});

new Chart(document.getElementById('sentRegChart'), {
  type: 'bar',
  data: {
    labels: D.sentiment_region.labels,
    datasets: [
      { label: 'Pos', data: D.sentiment_region.positive, backgroundColor: COLORS.pos },
      { label: 'Neg', data: D.sentiment_region.negative, backgroundColor: COLORS.neg },
      { label: 'Neu', data: D.sentiment_region.neutral, backgroundColor: COLORS.neu },
    ]
  },
  options: { plugins: { legend: { labels: { font: { size: 10 } } } }, scales: { x: { stacked: true, grid: { display: false }, ticks: { font: { size: 10 } } }, y: { stacked: true, display: false } } }
});

new Chart(document.getElementById('tlChart'), {
  type: 'bar',
  data: { labels: D.timeline.labels.map(d => d.slice(5)), datasets: [{ data: D.timeline.values, backgroundColor: '#007aff', borderRadius: 3 }] },
  options: { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { font: { size: 10 }, maxTicksLimit: 15 } }, y: { display: false } } }
});

const tbody = document.getElementById('artTable');
D.top_articles.forEach(a => {
  const cls = a.sentiment === 'positive' ? 'pos' : a.sentiment === 'negative' ? 'neg' : 'neu';
  const tr = document.createElement('tr');
  tr.innerHTML = '<td><span class="tag ' + cls + '">' + a.sentiment + '</span></td><td>' + a.title + '</td><td>' + a.region + '</td><td class="opinion-text" title="' + (a.opinion||'') + '">' + (a.opinion||'') + '</td><td>' + a.date + '</td>';
  tbody.appendChild(tr);
});
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────
# PROPOSAL D — Editorial / newspaper with hierarchical treemap
# ──────────────────────────────────────────────────────────────
TEMPLATE_D = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>nonews — Panorama Informativo</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #fafaf8; color: #1a1a1a; font-family: Georgia, 'Times New Roman', serif; }

/* ── Masthead ── */
.masthead { background: #fff; border-bottom: 3px double #1a1a1a; padding: 32px 48px 16px; text-align: center; }
.masthead h1 { font-size: 48px; font-weight: 900; letter-spacing: -2px; }
.masthead .edition { font-size: 13px; color: #999; font-family: system-ui, sans-serif; margin-top: 4px; text-transform: uppercase; letter-spacing: 2px; }
.masthead .dateline { font-size: 13px; color: #999; font-family: system-ui, sans-serif; margin-top: 4px; }

/* ── Layout ── */
.container { max-width: 1100px; margin: 0 auto; padding: 32px 48px; }
.section-rule { border: none; border-top: 2px solid #1a1a1a; margin: 32px 0 20px; }
.section-label { font-family: system-ui, sans-serif; font-size: 12px; text-transform: uppercase; letter-spacing: 2px; color: #666; margin-bottom: 16px; font-weight: 700; }

/* ── Hero / Summary ── */
.hero { background: #fff; border: 1px solid #e0e0e0; padding: 28px 32px; margin-bottom: 32px; border-radius: 4px; }
.hero h2 { font-size: 26px; line-height: 1.3; margin-bottom: 10px; }
.hero p { font-size: 15px; line-height: 1.7; color: #444; }
.sentiment-bar { display: flex; height: 10px; border-radius: 5px; overflow: hidden; margin: 16px 0 8px; }
.sentiment-bar .pos { background: #34a853; }
.sentiment-bar .neg { background: #ea4335; }
.sentiment-bar .neu { background: #dadce0; }
.sentiment-legend { font-family: system-ui, sans-serif; font-size: 13px; color: #666; display: flex; justify-content: space-between; }

/* ── Two-column grid ── */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; margin-bottom: 28px; }
.card { background: #fff; border: 1px solid #e0e0e0; border-radius: 4px; padding: 24px; }
.card h3 { font-family: system-ui, sans-serif; font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; color: #666; margin-bottom: 16px; font-weight: 700; }
.card canvas { max-height: 250px; }

/* ── News list ── */
.news-list { list-style: none; }
.news-item { padding: 14px 0; border-bottom: 1px solid #eee; display: grid; grid-template-columns: 80px 1fr; gap: 16px; align-items: start; }
.news-item:last-child { border-bottom: none; }
.news-sentiment { font-family: system-ui, sans-serif; font-size: 11px; font-weight: 700; text-transform: uppercase; padding: 4px 8px; border-radius: 3px; text-align: center; }
.news-sentiment.positive { background: #e6f4ea; color: #1e7e34; }
.news-sentiment.negative { background: #fce8e6; color: #c62828; }
.news-sentiment.neutral { background: #f1f3f4; color: #666; }
.news-title { font-size: 15px; line-height: 1.4; }
.news-meta { font-family: system-ui, sans-serif; font-size: 12px; color: #999; margin-top: 4px; }

/* ── Treemap hierarchy ── */
.treemap-container { background: #fff; border: 1px solid #e0e0e0; border-radius: 4px; padding: 24px; margin-bottom: 28px; }
.treemap-container h3 { font-family: system-ui, sans-serif; font-size: 12px; text-transform: uppercase; letter-spacing: 1.5px; color: #666; margin-bottom: 16px; font-weight: 700; }
.treemap-root { display: flex; gap: 16px; min-height: 320px; }
.treemap-branch { display: flex; flex: 1; gap: 0; border-radius: 6px; overflow: hidden; border: 1px solid #e0e0e0; }
.treemap-branch-label { writing-mode: vertical-lr; text-orientation: mixed; transform: rotate(180deg); font-family: system-ui, sans-serif; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; color: #555; display: flex; align-items: center; justify-content: center; padding: 8px 10px; background: #f5f5f0; min-width: 38px; }
.treemap-branch-content { display: flex; flex-direction: column; gap: 2px; flex: 1; padding: 2px; background: #fafafa; }
.treemap-region { border-radius: 4px; padding: 10px 14px; position: relative; overflow: hidden; cursor: default; transition: transform 0.15s; }
.treemap-region:hover { transform: scale(1.01); z-index: 2; }
.treemap-region-name { font-family: system-ui, sans-serif; font-size: 12px; font-weight: 700; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.3); margin-bottom: 4px; }
.treemap-region-count { font-family: system-ui, sans-serif; font-size: 10px; color: rgba(255,255,255,0.85); text-shadow: 0 1px 2px rgba(0,0,0,0.3); margin-bottom: 6px; }
.treemap-cats { display: flex; flex-wrap: wrap; gap: 3px; }
.treemap-cat-tag { font-family: system-ui, sans-serif; font-size: 9px; background: rgba(255,255,255,0.25); color: #fff; padding: 2px 6px; border-radius: 3px; text-shadow: 0 1px 1px rgba(0,0,0,0.2); }

/* ── Footer ── */
.footer { text-align: center; padding: 24px; color: #999; font-size: 12px; font-family: system-ui, sans-serif; border-top: 1px solid #eee; margin-top: 32px; }
</style>
</head>
<body>

<div class="masthead">
  <h1>nonews</h1>
  <div class="edition">Panorama informativo de Mexico</div>
  <div class="dateline" id="genDate"></div>
</div>

<div class="container">
  <!-- Hero summary -->
  <div class="hero">
    <h2 id="heroTitle">Panorama general</h2>
    <p id="heroText"></p>
    <div class="sentiment-bar"><div class="pos" id="barPos"></div><div class="neg" id="barNeg"></div><div class="neu" id="barNeu"></div></div>
    <div class="sentiment-legend"><span id="posLabel"></span><span id="negLabel"></span><span id="neuLabel"></span></div>
  </div>

  <!-- Charts row -->
  <div class="two-col">
    <div class="card"><h3>Sentimiento general</h3><canvas id="sentimentChart"></canvas></div>
    <div class="card"><h3>Regiones con mas cobertura</h3><canvas id="regionChart"></canvas></div>
  </div>

  <!-- Hierarchical treemap -->
  <div class="treemap-container">
    <h3>Desglose jerarquico: Nacional / Internacional &rarr; Region &rarr; Categoria</h3>
    <div class="treemap-root" id="treemapRoot"></div>
  </div>

  <!-- Recent news -->
  <hr class="section-rule">
  <div class="section-label">Noticias recientes</div>
  <ul class="news-list" id="newsList"></ul>

  <!-- Timeline -->
  <hr class="section-rule">
  <div class="section-label">Volumen diario (ultimos 15 dias)</div>
  <div class="card" style="margin-bottom:28px"><canvas id="timelineChart"></canvas></div>
</div>

<div class="footer">Generado el <span id="genDate2"></span> — nonews</div>

<script>
const DATA = __DATA__;
const HIERARCHY = __HIERARCHY__;

/* ── Populate header & hero ── */
document.getElementById('genDate').textContent = DATA.summary.generated_at;
document.getElementById('genDate2').textContent = DATA.summary.generated_at;

const s = DATA.summary;
document.getElementById('heroTitle').textContent = s.total + ' articulos analizados';
const dominant = s.positive_pct >= s.negative_pct ? 'positivo' : 'negativo';
document.getElementById('heroText').textContent =
  'El ' + Math.max(s.positive_pct, s.negative_pct) + '% de las noticias tiene un tono ' + dominant +
  '. Se cubren ' + s.regions_count + ' regiones distintas del pais.';

document.getElementById('barPos').style.width = s.positive_pct + '%';
document.getElementById('barNeg').style.width = s.negative_pct + '%';
document.getElementById('barNeu').style.width = s.neutral_pct + '%';
document.getElementById('posLabel').textContent = s.positive_pct + '% positivo';
document.getElementById('negLabel').textContent = s.negative_pct + '% negativo';
document.getElementById('neuLabel').textContent = s.neutral_pct + '% neutral';

/* ── Sentiment pie ── */
new Chart(document.getElementById('sentimentChart'), {
  type: 'pie',
  data: {
    labels: ['positive', 'negative', 'neutral'],
    datasets: [{ data: [
      DATA.sentiment.values[DATA.sentiment.labels.indexOf('positive')] || 0,
      DATA.sentiment.values[DATA.sentiment.labels.indexOf('negative')] || 0,
      DATA.sentiment.values[DATA.sentiment.labels.indexOf('neutral')] || 0
    ], backgroundColor: ['#34a853','#ea4335','#dadce0'] }]
  },
  options: { plugins: { legend: { position: 'bottom' } } }
});

/* ── Region bar chart ── */
new Chart(document.getElementById('regionChart'), {
  type: 'bar',
  data: { labels: DATA.region.labels, datasets: [{ data: DATA.region.values, backgroundColor: '#4285f4' }] },
  options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { grid: { display: false } } } }
});

/* ── Timeline (15 days) ── */
new Chart(document.getElementById('timelineChart'), {
  type: 'bar',
  data: { labels: DATA.timeline.labels.map(d => d.slice(5)), datasets: [{ data: DATA.timeline.values, backgroundColor: '#4285f4' }] },
  options: { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 15 } }, y: { grid: { color: '#eee' } } } }
});

/* ── Treemap hierarchy ── */
(function buildTreemap() {
  const root = document.getElementById('treemapRoot');
  const NATIONAL_COLOR = '#4285f4';
  const INTERNATIONAL_COLOR = '#fbbc04';
  const REGION_COLORS = [
    '#34a853','#ea4335','#fbbc04','#4285f4','#ff6d01','#46bdc6',
    '#7b61ff','#e8710a','#1a73e8','#d93025','#1e8e3e','#e52592',
    '#12b5cb','#9334e6','#f9ab00','#1967d2','#c5221f','#0d652d'
  ];

  function shadeColor(hex, percent) {
    const num = parseInt(hex.replace('#',''), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.min(255, Math.max(0, (num >> 16) + amt));
    const G = Math.min(255, Math.max(0, ((num >> 8) & 0x00FF) + amt));
    const B = Math.min(255, Math.max(0, (num & 0x0000FF) + amt));
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
  }

  function renderBranch(branchKey, branchData, accentColor) {
    const branchEl = document.createElement('div');
    branchEl.className = 'treemap-branch';

    const label = document.createElement('div');
    label.className = 'treemap-branch-label';
    label.textContent = branchKey === 'national' ? 'Nacional' : 'Internacional';
    label.style.borderRight = '3px solid ' + accentColor;
    branchEl.appendChild(label);

    const content = document.createElement('div');
    content.className = 'treemap-branch-content';

    const regions = Object.entries(branchData.regions)
      .sort((a, b) => b[1].total - a[1].total);

    const maxTotal = branchData.total || 1;
    let colorIdx = 0;

    regions.forEach(([regionName, regionData]) => {
      const fraction = regionData.total / maxTotal;
      const baseColor = REGION_COLORS[colorIdx % REGION_COLORS.length];
      colorIdx++;

      const regionEl = document.createElement('div');
      regionEl.className = 'treemap-region';
      regionEl.style.background = 'linear-gradient(135deg, ' + baseColor + ', ' + shadeColor(baseColor, -15) + ')';
      regionEl.style.minHeight = Math.max(48, Math.round(fraction * 200)) + 'px';
      regionEl.style.flexGrow = regionData.total;

      const nameEl = document.createElement('div');
      nameEl.className = 'treemap-region-name';
      nameEl.textContent = regionName;
      regionEl.appendChild(nameEl);

      const countEl = document.createElement('div');
      countEl.className = 'treemap-region-count';
      countEl.textContent = regionData.total + ' articulos';
      regionEl.appendChild(countEl);

      const catsEl = document.createElement('div');
      catsEl.className = 'treemap-cats';
      const sortedCats = Object.entries(regionData.categories)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 6);
      sortedCats.forEach(([cat, count]) => {
        const tag = document.createElement('span');
        tag.className = 'treemap-cat-tag';
        tag.textContent = cat + ' (' + count + ')';
        catsEl.appendChild(tag);
      });
      regionEl.appendChild(catsEl);

      content.appendChild(regionEl);
    });

    branchEl.appendChild(content);
    return branchEl;
  }

  if (HIERARCHY.national.total > 0) {
    root.appendChild(renderBranch('national', HIERARCHY.national, NATIONAL_COLOR));
  }
  if (HIERARCHY.international.total > 0) {
    root.appendChild(renderBranch('international', HIERARCHY.international, INTERNATIONAL_COLOR));
  }
})();

/* ── News list ── */
const list = document.getElementById('newsList');
DATA.top_articles.forEach(a => {
  const li = document.createElement('li');
  li.className = 'news-item';
  li.innerHTML = '<span class="news-sentiment ' + a.sentiment + '">' + a.sentiment + '</span><div><div class="news-title">' + a.title + '</div><div class="news-meta">' + a.region + ' — ' + a.date + '</div></div>';
  list.appendChild(li);
});
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────
# PROPOSAL D1 — Editorial / newspaper with drill-down navigation
# ──────────────────────────────────────────────────────────────
TEMPLATE_D1 = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>nonews — Explorador Informativo</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #fafaf8; color: #1a1a1a; font-family: Georgia, 'Times New Roman', serif; }

/* ── Masthead ── */
.masthead { background: #fff; border-bottom: 3px double #1a1a1a; padding: 28px 40px 14px; text-align: center; }
.masthead h1 { font-size: 44px; font-weight: 900; letter-spacing: -2px; }
.masthead .edition { font-size: 12px; color: #999; font-family: system-ui, sans-serif; margin-top: 2px; text-transform: uppercase; letter-spacing: 2px; }
.masthead .dateline { font-size: 12px; color: #999; font-family: system-ui, sans-serif; margin-top: 4px; }

/* ── Date filter bar ── */
.filter-bar { background: #fff; border-bottom: 1px solid #e0e0e0; padding: 12px 40px; display: flex; align-items: center; gap: 12px; font-family: system-ui, sans-serif; font-size: 13px; }
.filter-bar label { color: #666; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; font-size: 11px; }
.filter-bar input[type="date"] { border: 1px solid #ccc; border-radius: 4px; padding: 6px 10px; font-size: 13px; font-family: system-ui, sans-serif; background: #fafaf8; }
.filter-bar button { background: #1a1a1a; color: #fff; border: none; border-radius: 4px; padding: 7px 18px; font-size: 13px; font-family: system-ui, sans-serif; cursor: pointer; font-weight: 600; letter-spacing: 0.5px; transition: background 0.2s; }
.filter-bar button:hover { background: #333; }
.filter-bar .filter-status { margin-left: auto; color: #999; font-size: 12px; }

/* ── Charts section ── */
.container { max-width: 1200px; margin: 0 auto; padding: 24px 40px; }
.charts-row { display: grid; grid-template-columns: 1fr 1.4fr 1.2fr; gap: 20px; margin-bottom: 24px; }
.chart-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 4px; padding: 18px; }
.chart-card h3 { font-family: system-ui, sans-serif; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #666; margin-bottom: 12px; font-weight: 700; }
.chart-card canvas { max-height: 220px; }

/* ── Main content: drill-down + detail ── */
.main-content { display: grid; grid-template-columns: 340px 1fr; gap: 0; background: #fff; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden; min-height: 520px; margin-bottom: 32px; }

/* ── Left panel: drill-down ── */
.drill-panel { border-right: 1px solid #e0e0e0; display: flex; flex-direction: column; }
.drill-header { padding: 14px 18px; border-bottom: 1px solid #eee; font-family: system-ui, sans-serif; display: flex; align-items: center; gap: 8px; background: #f9f9f6; }
.drill-header .breadcrumb { font-size: 12px; color: #999; flex: 1; }
.drill-header .breadcrumb span { color: #1a1a1a; font-weight: 600; }
.drill-back { background: none; border: 1px solid #ccc; border-radius: 4px; padding: 4px 10px; font-size: 12px; font-family: system-ui, sans-serif; cursor: pointer; color: #555; transition: all 0.15s; }
.drill-back:hover { background: #eee; border-color: #999; }
.drill-back:disabled { opacity: 0.3; cursor: default; }
.drill-list { flex: 1; overflow-y: auto; padding: 8px 0; }
.drill-item { padding: 10px 18px; cursor: pointer; border-bottom: 1px solid #f5f5f5; transition: background 0.12s; display: flex; align-items: center; gap: 10px; }
.drill-item:hover { background: #f0efe8; }
.drill-item .item-label { flex: 1; font-size: 14px; line-height: 1.35; }
.drill-item .item-count { font-family: system-ui, sans-serif; font-size: 11px; color: #999; background: #f0f0f0; padding: 2px 8px; border-radius: 10px; white-space: nowrap; }
.drill-item .item-arrow { color: #ccc; font-size: 14px; }
.drill-item .sentiment-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.drill-item .sentiment-dot.positive { background: #34a853; }
.drill-item .sentiment-dot.negative { background: #ea4335; }
.drill-item .sentiment-dot.neutral { background: #dadce0; }
.drill-item .item-date { font-family: system-ui, sans-serif; font-size: 11px; color: #aaa; white-space: nowrap; }
.drill-item .item-title { font-size: 13px; line-height: 1.35; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ── Right panel: article detail ── */
.detail-panel { padding: 28px 32px; overflow-y: auto; max-height: 600px; }
.detail-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #bbb; text-align: center; }
.detail-placeholder .icon { font-size: 48px; margin-bottom: 16px; opacity: 0.4; }
.detail-placeholder p { font-size: 15px; font-style: italic; line-height: 1.6; }
.detail-article h2 { font-size: 22px; line-height: 1.35; margin-bottom: 12px; }
.detail-meta { font-family: system-ui, sans-serif; display: flex; align-items: center; gap: 10px; margin-bottom: 18px; flex-wrap: wrap; }
.detail-badge { padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
.detail-badge.positive { background: #e6f4ea; color: #1e7e34; }
.detail-badge.negative { background: #fce8e6; color: #c62828; }
.detail-badge.neutral { background: #f1f3f4; color: #666; }
.detail-meta .meta-item { font-size: 12px; color: #888; }
.detail-meta .meta-item strong { color: #555; }
.detail-section { margin-top: 20px; }
.detail-section h4 { font-family: system-ui, sans-serif; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #888; margin-bottom: 8px; font-weight: 700; border-bottom: 1px solid #eee; padding-bottom: 6px; }
.detail-section p { font-size: 15px; line-height: 1.7; color: #333; }
.detail-section .opinion-text { font-style: italic; color: #555; border-left: 3px solid #dadce0; padding-left: 16px; }

/* ── Footer ── */
.footer { text-align: center; padding: 20px; color: #999; font-size: 12px; font-family: system-ui, sans-serif; border-top: 1px solid #eee; margin-top: 24px; }
</style>
</head>
<body>

<div class="masthead">
  <h1>nonews</h1>
  <div class="edition">Explorador informativo de Mexico</div>
  <div class="dateline" id="genDate"></div>
</div>

<div class="filter-bar">
  <label>Desde:</label>
  <input type="date" id="dateFrom">
  <label>Hasta:</label>
  <input type="date" id="dateTo">
  <button id="applyFilter">Aplicar</button>
  <span class="filter-status" id="filterStatus"></span>
</div>

<div class="container">
  <!-- Charts -->
  <div class="charts-row">
    <div class="chart-card"><h3>Sentimiento general</h3><canvas id="sentimentChart"></canvas></div>
    <div class="chart-card"><h3>Regiones con mas cobertura</h3><canvas id="regionChart"></canvas></div>
    <div class="chart-card"><h3>Volumen diario</h3><canvas id="timelineChart"></canvas></div>
  </div>

  <!-- Main: drill-down + detail -->
  <div class="main-content">
    <div class="drill-panel">
      <div class="drill-header">
        <button class="drill-back" id="btnBack" disabled>&larr; Atras</button>
        <div class="breadcrumb" id="breadcrumb"><span>Inicio</span></div>
      </div>
      <div class="drill-list" id="drillList"></div>
    </div>
    <div class="detail-panel" id="detailPanel">
      <div class="detail-placeholder">
        <div class="icon">&#9776;</div>
        <p>Selecciona un articulo del panel izquierdo<br>para ver su detalle.</p>
      </div>
    </div>
  </div>
</div>

<div class="footer">Generado el <span id="genDate2"></span> — nonews</div>

<script>
const DATA = __DATA__;
const SIDEBAR = __SIDEBAR__;

/* ── Flatten all articles for filtering ── */
const ALL_ARTICLES = [];
['national','international'].forEach(scope => {
  Object.entries(SIDEBAR[scope].regions).forEach(([region, articles]) => {
    articles.forEach(a => {
      ALL_ARTICLES.push({ ...a, scope });
    });
  });
});

/* ── State ── */
let filteredArticles = ALL_ARTICLES.slice();
let drillPath = []; // stack of {level, label, data}
let sentimentChart, regionChart, timelineChart;

/* ── Header ── */
document.getElementById('genDate').textContent = DATA.summary.generated_at;
document.getElementById('genDate2').textContent = DATA.summary.generated_at;

/* ── Date range init ── */
const dates = ALL_ARTICLES.map(a => a.date).filter(Boolean).sort();
if (dates.length) {
  document.getElementById('dateFrom').value = dates[0];
  document.getElementById('dateTo').value = dates[dates.length - 1];
}

/* ── Charts (initial) ── */
function buildCharts(articles) {
  // Sentiment counts
  const sentCounts = { positive: 0, negative: 0, neutral: 0 };
  articles.forEach(a => { sentCounts[a.sentiment || 'neutral']++; });
  const sentLabels = [], sentValues = [];
  [['positive','Positivo'],['negative','Negativo'],['neutral','Neutral']].forEach(([k,l]) => {
    if (sentCounts[k] > 0) { sentLabels.push(l); sentValues.push(sentCounts[k]); }
  });

  // Region counts (top 15)
  const regCounts = {};
  articles.forEach(a => { if (a.region) regCounts[a.region] = (regCounts[a.region]||0) + 1; });
  const sortedRegions = Object.entries(regCounts).sort((a,b) => b[1]-a[1]).slice(0,15);

  // Timeline
  const dayCounts = {};
  articles.forEach(a => { if (a.date) dayCounts[a.date] = (dayCounts[a.date]||0) + 1; });
  const sortedDays = Object.keys(dayCounts).sort();

  if (sentimentChart) sentimentChart.destroy();
  if (regionChart) regionChart.destroy();
  if (timelineChart) timelineChart.destroy();

  sentimentChart = new Chart(document.getElementById('sentimentChart'), {
    type: 'pie',
    data: { labels: sentLabels, datasets: [{ data: sentValues, backgroundColor: ['#34a853','#ea4335','#dadce0'] }] },
    options: { plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } } }
  });

  regionChart = new Chart(document.getElementById('regionChart'), {
    type: 'bar',
    data: { labels: sortedRegions.map(r=>r[0]), datasets: [{ data: sortedRegions.map(r=>r[1]), backgroundColor: '#4285f4' }] },
    options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { font: { size: 10 } } }, y: { grid: { display: false }, ticks: { font: { size: 11 } } } } }
  });

  timelineChart = new Chart(document.getElementById('timelineChart'), {
    type: 'bar',
    data: { labels: sortedDays.map(d=>d.slice(5)), datasets: [{ data: sortedDays.map(d=>dayCounts[d]), backgroundColor: '#4285f4' }] },
    options: { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 12, font: { size: 10 } } }, y: { grid: { color: '#eee' }, ticks: { font: { size: 10 } } } } }
  });
}

buildCharts(ALL_ARTICLES);
document.getElementById('filterStatus').textContent = ALL_ARTICLES.length + ' articulos';

/* ── Date filter ── */
document.getElementById('applyFilter').addEventListener('click', function() {
  const from = document.getElementById('dateFrom').value;
  const to = document.getElementById('dateTo').value;
  filteredArticles = ALL_ARTICLES.filter(a => {
    if (!a.date) return true;
    if (from && a.date < from) return false;
    if (to && a.date > to) return false;
    return true;
  });
  document.getElementById('filterStatus').textContent = filteredArticles.length + ' articulos';
  buildCharts(filteredArticles);
  // Reset drill-down
  drillPath = [];
  renderDrillLevel();
});

/* ── Drill-down navigation ── */
function renderDrillLevel() {
  const list = document.getElementById('drillList');
  const btnBack = document.getElementById('btnBack');
  const breadcrumb = document.getElementById('breadcrumb');

  list.innerHTML = '';
  btnBack.disabled = drillPath.length === 0;

  // Build breadcrumb
  let crumbs = '<span>Inicio</span>';
  drillPath.forEach((p, i) => {
    crumbs += ' &rsaquo; <span>' + p.label + '</span>';
  });
  breadcrumb.innerHTML = crumbs;

  if (drillPath.length === 0) {
    // Level 0: show Nacional / Internacional
    const scopes = [
      { key: 'national', label: 'Nacional' },
      { key: 'international', label: 'Internacional' }
    ];
    scopes.forEach(sc => {
      const count = filteredArticles.filter(a => a.scope === sc.key).length;
      if (count === 0) return;
      const div = document.createElement('div');
      div.className = 'drill-item';
      div.innerHTML = '<div class="item-label">' + sc.label + '</div><div class="item-count">' + count + '</div><div class="item-arrow">&rsaquo;</div>';
      div.addEventListener('click', function() {
        drillPath.push({ level: 'scope', key: sc.key, label: sc.label });
        renderDrillLevel();
      });
      list.appendChild(div);
    });
  } else if (drillPath.length === 1) {
    // Level 1: show regions within scope
    const scopeKey = drillPath[0].key;
    const regionArticles = {};
    filteredArticles.filter(a => a.scope === scopeKey).forEach(a => {
      if (!regionArticles[a.region]) regionArticles[a.region] = [];
      regionArticles[a.region].push(a);
    });
    const sortedRegions = Object.entries(regionArticles).sort((a,b) => b[1].length - a[1].length);
    sortedRegions.forEach(([region, arts]) => {
      const div = document.createElement('div');
      div.className = 'drill-item';
      div.innerHTML = '<div class="item-label">' + region + '</div><div class="item-count">' + arts.length + '</div><div class="item-arrow">&rsaquo;</div>';
      div.addEventListener('click', function() {
        drillPath.push({ level: 'region', key: region, label: region, data: arts });
        renderDrillLevel();
      });
      list.appendChild(div);
    });
  } else if (drillPath.length === 2) {
    // Level 2: show articles within region
    const articles = drillPath[1].data || [];
    const sorted = articles.slice().sort((a,b) => (b.date||'').localeCompare(a.date||''));
    sorted.forEach(a => {
      const div = document.createElement('div');
      div.className = 'drill-item';
      div.innerHTML = '<div class="sentiment-dot ' + a.sentiment + '"></div><div class="item-title" title="' + escHtml(a.title) + '">' + escHtml(a.title) + '</div><div class="item-date">' + (a.date||'') + '</div>';
      div.addEventListener('click', function() {
        showArticleDetail(a);
        // Highlight selected
        list.querySelectorAll('.drill-item').forEach(el => el.style.background = '');
        div.style.background = '#e8e7df';
      });
      list.appendChild(div);
    });
  }
}

function escHtml(s) {
  return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

document.getElementById('btnBack').addEventListener('click', function() {
  if (drillPath.length > 0) {
    drillPath.pop();
    renderDrillLevel();
  }
});

/* ── Article detail panel ── */
function showArticleDetail(a) {
  const panel = document.getElementById('detailPanel');
  const sentLabel = { positive: 'Positivo', negative: 'Negativo', neutral: 'Neutral' };
  let html = '<div class="detail-article">';
  html += '<h2>' + escHtml(a.title) + '</h2>';
  html += '<div class="detail-meta">';
  html += '<span class="detail-badge ' + a.sentiment + '">' + (sentLabel[a.sentiment]||a.sentiment) + '</span>';
  html += '<span class="meta-item"><strong>Region:</strong> ' + escHtml(a.region) + '</span>';
  html += '<span class="meta-item"><strong>Fecha:</strong> ' + (a.date||'N/A') + '</span>';
  if (a.source) html += '<span class="meta-item"><strong>Fuente:</strong> ' + escHtml(a.source) + '</span>';
  html += '</div>';
  if (a.summary) {
    html += '<div class="detail-section"><h4>Resumen</h4><p>' + escHtml(a.summary) + '</p></div>';
  }
  if (a.opinion) {
    html += '<div class="detail-section"><h4>Opinion</h4><p class="opinion-text">' + escHtml(a.opinion) + '</p></div>';
  }
  html += '</div>';
  panel.innerHTML = html;
}

/* ── Init drill-down ── */
renderDrillLevel();
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────
# PROPOSAL D3 — Editorial / newspaper with sidebar tree navigation
# ──────────────────────────────────────────────────────────────
TEMPLATE_D3 = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>nonews — Panorama Informativo</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #fafaf8; color: #1a1a1a; font-family: Georgia, 'Times New Roman', serif; }

/* ── Masthead ── */
.masthead { background: #fff; border-bottom: 3px double #1a1a1a; padding: 20px 32px 12px; text-align: center; margin-left: 260px; }
.masthead h1 { font-size: 42px; font-weight: 900; letter-spacing: -2px; }
.masthead .edition { font-size: 12px; color: #999; font-family: system-ui, sans-serif; margin-top: 2px; text-transform: uppercase; letter-spacing: 2px; }

/* ── Sidebar ── */
.sidebar {
  position: fixed; top: 0; left: 0; width: 260px; height: 100vh;
  background: #fff; border-right: 2px solid #1a1a1a;
  overflow-y: auto; z-index: 100;
  font-family: system-ui, sans-serif;
}
.sidebar-header {
  padding: 16px 16px 12px; border-bottom: 1px solid #e0e0e0;
  text-align: center;
}
.sidebar-header .logo { font-family: Georgia, serif; font-size: 22px; font-weight: 900; letter-spacing: -1px; }
.sidebar-header .sub { font-size: 10px; color: #999; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 2px; }

/* ── Date filter ── */
.date-filter {
  padding: 12px 16px; border-bottom: 1px solid #e0e0e0;
  background: #fafaf8;
}
.date-filter label { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #666; font-weight: 700; display: block; margin-bottom: 6px; }
.date-row { display: flex; gap: 6px; align-items: center; margin-bottom: 8px; }
.date-row input {
  flex: 1; padding: 5px 6px; border: 1px solid #ccc; border-radius: 3px;
  font-size: 12px; font-family: system-ui, sans-serif; background: #fff;
}
.date-row span { font-size: 11px; color: #999; }
.btn-filtrar {
  width: 100%; padding: 6px; background: #1a1a1a; color: #fff; border: none;
  border-radius: 3px; font-size: 12px; font-family: system-ui, sans-serif;
  cursor: pointer; font-weight: 600; letter-spacing: 0.5px;
}
.btn-filtrar:hover { background: #333; }
.filter-summary {
  font-size: 11px; color: #666; margin-top: 6px; line-height: 1.4;
  display: none;
}
.filter-summary.active { display: block; }

/* ── Tree nav ── */
.tree-nav { padding: 8px 0; }
.tree-scope {
  padding: 8px 16px; font-size: 13px; font-weight: 700; cursor: pointer;
  display: flex; align-items: center; gap: 6px; color: #1a1a1a;
  border-bottom: 1px solid #f0f0f0; user-select: none;
}
.tree-scope:hover { background: #f5f5f0; }
.tree-scope .arrow { font-size: 10px; transition: transform 0.2s; display: inline-block; width: 12px; }
.tree-scope .arrow.open { transform: rotate(90deg); }
.tree-scope .scope-count { margin-left: auto; font-size: 11px; color: #999; font-weight: 400; }
.tree-region-group { display: none; }
.tree-region-group.open { display: block; }
.tree-region {
  padding: 6px 16px 6px 34px; font-size: 12px; cursor: pointer;
  display: flex; align-items: center; gap: 6px; color: #444;
  user-select: none;
}
.tree-region:hover { background: #f5f5f0; color: #1a1a1a; }
.tree-region .arrow { font-size: 9px; transition: transform 0.2s; display: inline-block; width: 10px; }
.tree-region .arrow.open { transform: rotate(90deg); }
.tree-region .region-count { margin-left: auto; font-size: 10px; color: #aaa; }
.tree-articles { display: none; }
.tree-articles.open { display: block; }
.tree-article {
  padding: 4px 16px 4px 54px; font-size: 11px; color: #666;
  cursor: pointer; line-height: 1.4; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;
}
.tree-article:hover { background: #f5f5f0; color: #1a1a1a; }
.tree-article.active { background: #eef1f5; color: #1a1a1a; font-weight: 600; }
.tree-article .sent-dot {
  display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  margin-right: 4px; vertical-align: middle;
}
.tree-region.active { background: #eef1f5; color: #1a1a1a; font-weight: 600; }
.tree-scope.active { background: #eef1f5; }

/* ── Main content ── */
.main { margin-left: 260px; padding: 0 32px 32px; }

/* ── Summary bar ── */
.summary-strip {
  background: #fff; border: 1px solid #e0e0e0; padding: 20px 24px;
  margin: 20px 0; border-radius: 4px;
}
.summary-strip h2 { font-size: 22px; line-height: 1.3; margin-bottom: 6px; }
.summary-strip p { font-size: 14px; color: #555; line-height: 1.6; }
.sentiment-bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin: 12px 0 6px; }
.sentiment-bar .pos { background: #588157; }
.sentiment-bar .neg { background: #bc4749; }
.sentiment-bar .neu { background: #b5b5b5; }
.sentiment-legend { font-family: system-ui, sans-serif; font-size: 12px; color: #666; display: flex; justify-content: space-between; }

/* ── Charts ── */
.charts-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 24px; }
.chart-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 4px; padding: 18px; }
.chart-card h3 { font-family: system-ui, sans-serif; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #666; margin-bottom: 12px; font-weight: 700; }
.chart-card canvas { max-height: 200px; }

/* ── Section label ── */
.section-rule { border: none; border-top: 2px solid #1a1a1a; margin: 24px 0 16px; }
.section-label { font-family: system-ui, sans-serif; font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #666; margin-bottom: 14px; font-weight: 700; }

/* ── Article cards grid ── */
.articles-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
.article-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 4px;
  padding: 18px; cursor: pointer; transition: box-shadow 0.15s;
}
.article-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.article-card.active { border-color: #1a1a1a; box-shadow: 0 2px 8px rgba(0,0,0,0.12); }
.article-card .card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.badge { padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 700; text-transform: uppercase; font-family: system-ui, sans-serif; }
.badge.positive { background: #eef2ee; color: #588157; }
.badge.negative { background: #f2eded; color: #bc4749; }
.badge.neutral { background: #f0f0f0; color: #888; }
.region-tag { font-size: 10px; color: #888; font-family: system-ui, sans-serif; background: #f5f5f0; padding: 2px 6px; border-radius: 8px; }
.article-card h4 { font-size: 15px; line-height: 1.4; margin-bottom: 6px; }
.article-card .card-meta { font-size: 11px; color: #999; font-family: system-ui, sans-serif; }
.article-card .card-opinion { font-size: 13px; color: #555; line-height: 1.5; margin-top: 8px; font-style: italic; }
.article-card .card-opinion::before { content: '\201C'; }
.article-card .card-opinion::after { content: '\201D'; }

/* ── Article detail ── */
.article-detail {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 4px;
  padding: 28px 32px; margin-bottom: 24px; display: none;
}
.article-detail.active { display: block; }
.article-detail .back-btn {
  font-family: system-ui, sans-serif; font-size: 12px; color: #666;
  cursor: pointer; margin-bottom: 16px; display: inline-block;
  border: 1px solid #ccc; padding: 4px 12px; border-radius: 3px;
  background: #fafaf8;
}
.article-detail .back-btn:hover { background: #f0f0f0; }
.article-detail h2 { font-size: 24px; line-height: 1.3; margin-bottom: 12px; }
.article-detail .detail-meta { font-family: system-ui, sans-serif; font-size: 13px; color: #888; margin-bottom: 16px; display: flex; gap: 12px; align-items: center; }
.article-detail .detail-opinion { font-size: 16px; line-height: 1.7; color: #333; font-style: italic; border-left: 3px solid #b5b5b5; padding-left: 16px; margin-top: 12px; }

/* ── Footer ── */
.footer { text-align: center; padding: 20px; color: #999; font-size: 11px; font-family: system-ui, sans-serif; border-top: 1px solid #eee; margin-top: 16px; }

/* ── No results ── */
.no-results { text-align: center; padding: 40px; color: #999; font-style: italic; display: none; }
</style>
</head>
<body>

<!-- ── Sidebar ── -->
<div class="sidebar">
  <div class="sidebar-header">
    <div class="logo">nonews</div>
    <div class="sub">Panorama Informativo</div>
  </div>

  <div class="date-filter">
    <label>Rango de fechas</label>
    <div class="date-row">
      <input type="date" id="dateFrom" title="Desde">
      <span>a</span>
      <input type="date" id="dateTo" title="Hasta">
    </div>
    <button class="btn-filtrar" id="btnFiltrar">Filtrar</button>
    <div class="filter-summary" id="filterSummary"></div>
  </div>

  <div class="tree-nav" id="treeNav"></div>
</div>

<!-- ── Masthead ── -->
<div class="masthead">
  <h1>nonews</h1>
  <div class="edition">Resumen del panorama informativo de M&eacute;xico</div>
  <div class="edition" id="genDate"></div>
</div>

<!-- ── Main content ── -->
<div class="main">

  <div class="summary-strip" id="summaryStrip">
    <h2 id="summaryTitle">Panorama general</h2>
    <p id="summaryText"></p>
    <div class="sentiment-bar"><div class="pos" id="barPos"></div><div class="neg" id="barNeg"></div><div class="neu" id="barNeu"></div></div>
    <div class="sentiment-legend"><span id="posLabel"></span><span id="negLabel"></span><span id="neuLabel"></span></div>
  </div>

  <div class="charts-row">
    <div class="chart-card"><h3>Sentimiento</h3><canvas id="sentimentChart"></canvas></div>
    <div class="chart-card"><h3>Regiones</h3><canvas id="regionChart"></canvas></div>
    <div class="chart-card"><h3>Volumen diario</h3><canvas id="timelineChart"></canvas></div>
  </div>

  <hr class="section-rule">
  <div class="section-label" id="articlesSectionLabel">Articulos</div>

  <div class="article-detail" id="articleDetail">
    <span class="back-btn" id="backBtn">&larr; Volver</span>
    <h2 id="detailTitle"></h2>
    <div class="detail-meta">
      <span class="badge" id="detailBadge"></span>
      <span class="region-tag" id="detailRegion"></span>
      <span id="detailDate"></span>
    </div>
    <div class="detail-opinion" id="detailOpinion"></div>
  </div>

  <div class="articles-grid" id="articlesGrid"></div>
  <div class="no-results" id="noResults">No hay articulos para mostrar.</div>
</div>

<div class="footer">Generado el <span id="genDate2"></span> — nonews</div>

<script>
const DATA = __DATA__;
const SIDEBAR = __SIDEBAR__;

const SENTIMENT_COLORS = { positive: '#588157', negative: '#bc4749', neutral: '#b5b5b5' };

/* ── Flatten all articles from sidebar data ── */
const ALL_ARTICLES = [];
['national', 'international'].forEach(scope => {
  Object.keys(SIDEBAR[scope].regions).forEach(region => {
    SIDEBAR[scope].regions[region].forEach(a => {
      ALL_ARTICLES.push({ ...a, scope });
    });
  });
});

/* ── State ── */
let currentFilter = { scope: null, region: null, articleIdx: null, dateFrom: null, dateTo: null };
let charts = {};

/* ── Date helpers ── */
function parseDate(s) { return s ? new Date(s + 'T00:00:00') : null; }
function inDateRange(a, from, to) {
  if (!a.date) return true;
  const d = parseDate(a.date);
  if (from && d < from) return false;
  if (to && d > to) return false;
  return true;
}

/* ── Get filtered articles ── */
function getFilteredArticles() {
  let arts = ALL_ARTICLES.slice();
  const from = currentFilter.dateFrom ? parseDate(currentFilter.dateFrom) : null;
  const to = currentFilter.dateTo ? parseDate(currentFilter.dateTo) : null;
  arts = arts.filter(a => inDateRange(a, from, to));
  if (currentFilter.scope && currentFilter.region) {
    arts = arts.filter(a => a.scope === currentFilter.scope && a.region === currentFilter.region);
  } else if (currentFilter.scope) {
    arts = arts.filter(a => a.scope === currentFilter.scope);
  }
  return arts;
}

/* ── Compute sentiment stats from article list ── */
function computeSentiment(arts) {
  const counts = { positive: 0, negative: 0, neutral: 0 };
  arts.forEach(a => { counts[a.sentiment || 'neutral']++; });
  const total = arts.length || 1;
  return {
    labels: Object.keys(counts).filter(k => counts[k] > 0),
    values: Object.values(counts).filter(v => v > 0),
    counts,
    total: arts.length,
    pct: {
      positive: Math.round(counts.positive / total * 1000) / 10,
      negative: Math.round(counts.negative / total * 1000) / 10,
      neutral: Math.round(counts.neutral / total * 1000) / 10,
    }
  };
}

/* ── Compute region counts ── */
function computeRegions(arts) {
  const counts = {};
  arts.forEach(a => { counts[a.region] = (counts[a.region] || 0) + 1; });
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 15);
  return { labels: sorted.map(s => s[0]), values: sorted.map(s => s[1]) };
}

/* ── Compute timeline ── */
function computeTimeline(arts) {
  const counts = {};
  arts.forEach(a => { if (a.date) counts[a.date] = (counts[a.date] || 0) + 1; });
  const sorted = Object.keys(counts).sort().slice(-30);
  return { labels: sorted, values: sorted.map(d => counts[d]) };
}

/* ── Build / update charts ── */
function updateCharts(arts) {
  const sent = computeSentiment(arts);
  const reg = computeRegions(arts);
  const tl = computeTimeline(arts);

  if (charts.sentiment) charts.sentiment.destroy();
  if (charts.region) charts.region.destroy();
  if (charts.timeline) charts.timeline.destroy();

  charts.sentiment = new Chart(document.getElementById('sentimentChart'), {
    type: 'pie',
    data: { labels: sent.labels, datasets: [{ data: sent.values, backgroundColor: sent.labels.map(l => SENTIMENT_COLORS[l]), borderWidth: 1, borderColor: '#fff' }] },
    options: { plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } } }
  });

  charts.region = new Chart(document.getElementById('regionChart'), {
    type: 'bar',
    data: { labels: reg.labels, datasets: [{ data: reg.values, backgroundColor: '#457b9d', borderRadius: 3 }] },
    options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { font: { size: 10 } } }, y: { grid: { display: false }, ticks: { font: { size: 10 } } } } }
  });

  charts.timeline = new Chart(document.getElementById('timelineChart'), {
    type: 'bar',
    data: { labels: tl.labels.map(d => d.slice(5)), datasets: [{ data: tl.values, backgroundColor: '#457b9d', borderRadius: 3 }] },
    options: { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 10, font: { size: 10 } } }, y: { grid: { color: '#eee' }, ticks: { font: { size: 10 } } } } }
  });
}

/* ── Update summary strip ── */
function updateSummary(arts) {
  const sent = computeSentiment(arts);
  const s = sent.pct;
  let titleSuffix = '';
  if (currentFilter.scope && currentFilter.region) {
    titleSuffix = ' — ' + currentFilter.region;
  } else if (currentFilter.scope) {
    titleSuffix = ' — ' + (currentFilter.scope === 'national' ? 'Nacional' : 'Internacional');
  }
  document.getElementById('summaryTitle').textContent = sent.total + ' articulos' + titleSuffix;
  const dominant = s.positive >= s.negative && s.positive >= s.neutral ? 'positivo'
    : s.negative >= s.positive && s.negative >= s.neutral ? 'negativo' : 'neutral';
  document.getElementById('summaryText').textContent =
    'El ' + Math.max(s.positive, s.negative, s.neutral) + '% de las noticias tiene un tono ' + dominant +
    '. Se cubren ' + new Set(arts.map(a => a.region)).size + ' regiones distintas.';
  document.getElementById('barPos').style.width = s.positive + '%';
  document.getElementById('barNeg').style.width = s.negative + '%';
  document.getElementById('barNeu').style.width = s.neutral + '%';
  document.getElementById('posLabel').textContent = s.positive + '% positivo';
  document.getElementById('negLabel').textContent = s.negative + '% negativo';
  document.getElementById('neuLabel').textContent = s.neutral + '% neutral';
}

/* ── Render article cards ── */
function renderArticles(arts) {
  const grid = document.getElementById('articlesGrid');
  const noRes = document.getElementById('noResults');
  grid.innerHTML = '';
  if (arts.length === 0) { noRes.style.display = 'block'; return; }
  noRes.style.display = 'none';

  arts.slice(0, 30).forEach((a, i) => {
    const card = document.createElement('div');
    card.className = 'article-card';
    card.innerHTML =
      '<div class="card-header"><span class="badge ' + a.sentiment + '">' + a.sentiment + '</span><span class="region-tag">' + a.region + '</span></div>' +
      '<h4>' + escHtml(a.title) + '</h4>' +
      '<div class="card-meta">' + a.date + '</div>' +
      (a.opinion ? '<div class="card-opinion">' + escHtml(a.opinion.substring(0, 120)) + (a.opinion.length > 120 ? '...' : '') + '</div>' : '');
    card.addEventListener('click', () => showDetail(a));
    grid.appendChild(card);
  });
}

function escHtml(s) {
  return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ── Show article detail ── */
function showDetail(a) {
  document.getElementById('articlesGrid').style.display = 'none';
  document.getElementById('noResults').style.display = 'none';
  const detail = document.getElementById('articleDetail');
  detail.classList.add('active');
  document.getElementById('detailTitle').textContent = a.title;
  const badge = document.getElementById('detailBadge');
  badge.textContent = a.sentiment;
  badge.className = 'badge ' + a.sentiment;
  document.getElementById('detailRegion').textContent = a.region;
  document.getElementById('detailDate').textContent = a.date;
  document.getElementById('detailOpinion').textContent = a.opinion || 'Sin opinion editorial.';
  document.getElementById('detailOpinion').style.display = a.opinion ? 'block' : 'none';
  document.getElementById('articlesSectionLabel').textContent = 'Detalle del articulo';
}

function hideDetail() {
  document.getElementById('articleDetail').classList.remove('active');
  document.getElementById('articlesGrid').style.display = '';
  document.getElementById('articlesSectionLabel').textContent = 'Articulos';
}

document.getElementById('backBtn').addEventListener('click', hideDetail);

/* ── Build sidebar tree ── */
function buildTree() {
  const nav = document.getElementById('treeNav');
  nav.innerHTML = '';
  const from = currentFilter.dateFrom ? parseDate(currentFilter.dateFrom) : null;
  const to = currentFilter.dateTo ? parseDate(currentFilter.dateTo) : null;

  const scopeLabels = { national: 'Nacional', international: 'Internacional' };

  ['national', 'international'].forEach(scope => {
    const regions = SIDEBAR[scope].regions;
    // Filter articles by date for counting
    let scopeArts = [];
    Object.keys(regions).forEach(region => {
      regions[region].forEach(a => {
        if (inDateRange(a, from, to)) scopeArts.push({ ...a, scope, region });
      });
    });

    if (scopeArts.length === 0) return;

    // Scope node
    const scopeEl = document.createElement('div');
    scopeEl.className = 'tree-scope';
    if (currentFilter.scope === scope && !currentFilter.region) scopeEl.classList.add('active');
    scopeEl.innerHTML = '<span class="arrow">&#9654;</span> ' + scopeLabels[scope] + '<span class="scope-count">' + scopeArts.length + '</span>';
    const scopeGroup = document.createElement('div');
    scopeGroup.className = 'tree-region-group';
    if (currentFilter.scope === scope) { scopeGroup.classList.add('open'); scopeEl.querySelector('.arrow').classList.add('open'); }

    scopeEl.addEventListener('click', () => {
      currentFilter.scope = scope;
      currentFilter.region = null;
      hideDetail();
      refresh();
    });

    // Region nodes
    Object.keys(regions).sort().forEach(region => {
      const regionArts = regions[region].filter(a => inDateRange(a, from, to));
      if (regionArts.length === 0) return;

      const regionEl = document.createElement('div');
      regionEl.className = 'tree-region';
      if (currentFilter.scope === scope && currentFilter.region === region) regionEl.classList.add('active');
      regionEl.innerHTML = '<span class="arrow">&#9654;</span> ' + region + '<span class="region-count">' + regionArts.length + '</span>';
      const articlesEl = document.createElement('div');
      articlesEl.className = 'tree-articles';
      if (currentFilter.scope === scope && currentFilter.region === region) { articlesEl.classList.add('open'); regionEl.querySelector('.arrow').classList.add('open'); }

      regionEl.addEventListener('click', (e) => {
        e.stopPropagation();
        if (currentFilter.scope === scope && currentFilter.region === region) {
          currentFilter.region = null;
        } else {
          currentFilter.scope = scope;
          currentFilter.region = region;
        }
        hideDetail();
        refresh();
      });

      // Article titles
      regionArts.forEach(a => {
        const artEl = document.createElement('div');
        artEl.className = 'tree-article';
        artEl.innerHTML = '<span class="sent-dot" style="background:' + SENTIMENT_COLORS[a.sentiment] + '"></span>' + escHtml(a.title);
        artEl.title = a.title;
        artEl.addEventListener('click', (e) => {
          e.stopPropagation();
          currentFilter.scope = scope;
          currentFilter.region = region;
          hideDetail();
          refresh();
          setTimeout(() => showDetail(a), 50);
        });
        articlesEl.appendChild(artEl);
      });

      scopeGroup.appendChild(regionEl);
      scopeGroup.appendChild(articlesEl);
    });

    nav.appendChild(scopeEl);
    nav.appendChild(scopeGroup);
  });
}

/* ── Master refresh ── */
function refresh() {
  const arts = getFilteredArticles();
  buildTree();
  updateSummary(arts);
  updateCharts(arts);
  renderArticles(arts);
  updateFilterSummary(arts);
}

/* ── Filter summary ── */
function updateFilterSummary(arts) {
  const el = document.getElementById('filterSummary');
  if (currentFilter.dateFrom || currentFilter.dateTo) {
    const fromStr = currentFilter.dateFrom || '...';
    const toStr = currentFilter.dateTo || '...';
    el.textContent = 'Mostrando ' + arts.length + ' articulos de ' + fromStr + ' a ' + toStr;
    el.classList.add('active');
  } else {
    el.classList.remove('active');
  }
}

/* ── Date filter button ── */
document.getElementById('btnFiltrar').addEventListener('click', () => {
  const from = document.getElementById('dateFrom').value;
  const to = document.getElementById('dateTo').value;
  currentFilter.dateFrom = from || null;
  currentFilter.dateTo = to || null;
  hideDetail();
  refresh();
});

/* ── Init ── */
document.getElementById('genDate').textContent = DATA.summary.generated_at;
document.getElementById('genDate2').textContent = DATA.summary.generated_at;

refresh();
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────
# PROPOSAL D2 — Editorial / newspaper with accordion hierarchy + date filter
# ──────────────────────────────────────────────────────────────
TEMPLATE_D2 = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>nonews — Panorama Informativo</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #fafaf8; color: #1a1a1a; font-family: Georgia, 'Times New Roman', serif; }

/* ── Masthead ── */
.masthead { background: #fff; border-bottom: 3px double #1a1a1a; padding: 28px 40px 14px; text-align: center; }
.masthead h1 { font-size: 44px; font-weight: 900; letter-spacing: -2px; }
.masthead .edition { font-size: 12px; color: #999; font-family: system-ui, sans-serif; margin-top: 4px; text-transform: uppercase; letter-spacing: 2px; }
.masthead .dateline { font-size: 12px; color: #999; font-family: system-ui, sans-serif; margin-top: 2px; }

/* ── Date filter bar ── */
.filter-bar { background: #fff; border-bottom: 1px solid #e0e0e0; padding: 14px 40px; display: flex; align-items: center; gap: 16px; font-family: system-ui, sans-serif; }
.filter-bar label { font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: #666; font-weight: 700; white-space: nowrap; }
.filter-bar .range-group { display: flex; align-items: center; gap: 10px; flex: 1; }
.filter-bar input[type="date"] { font-family: system-ui, sans-serif; font-size: 13px; padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; background: #fafaf8; color: #333; outline: none; transition: border-color 0.2s; }
.filter-bar input[type="date"]:focus { border-color: #4285f4; }
.filter-bar .range-sep { color: #999; font-size: 13px; }
.filter-bar .filter-count { font-size: 12px; color: #888; margin-left: auto; white-space: nowrap; }
.filter-bar .filter-count strong { color: #333; }

/* ── Layout ── */
.container { max-width: 1200px; margin: 0 auto; padding: 24px 40px; }
.section-rule { border: none; border-top: 2px solid #1a1a1a; margin: 28px 0 18px; }
.section-label { font-family: system-ui, sans-serif; font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #666; margin-bottom: 14px; font-weight: 700; }

/* ── Hero / Summary ── */
.hero { background: #fff; border: 1px solid #e0e0e0; padding: 24px 28px; margin-bottom: 24px; border-radius: 4px; }
.hero h2 { font-size: 24px; line-height: 1.3; margin-bottom: 8px; }
.hero p { font-size: 14px; line-height: 1.7; color: #444; }
.sentiment-bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin: 14px 0 6px; }
.sentiment-bar .pos { background: #34a853; }
.sentiment-bar .neg { background: #ea4335; }
.sentiment-bar .neu { background: #dadce0; }
.sentiment-legend { font-family: system-ui, sans-serif; font-size: 12px; color: #666; display: flex; justify-content: space-between; }

/* ── Main split: accordion + detail panel ── */
.main-split { display: grid; grid-template-columns: 1fr 360px; gap: 24px; margin-bottom: 28px; min-height: 500px; }

/* ── Accordion ── */
.accordion-panel { background: #fff; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden; }
.accordion-panel > .panel-header { font-family: system-ui, sans-serif; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #666; font-weight: 700; padding: 14px 18px 10px; border-bottom: 1px solid #eee; }

.acc-scope { border-bottom: 1px solid #eee; }
.acc-scope:last-child { border-bottom: none; }
.acc-scope-header { display: flex; align-items: center; padding: 12px 18px; cursor: pointer; user-select: none; transition: background 0.15s; font-family: system-ui, sans-serif; }
.acc-scope-header:hover { background: #f5f5f0; }
.acc-scope-header .arrow { width: 18px; height: 18px; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #999; transition: transform 0.25s; margin-right: 10px; flex-shrink: 0; }
.acc-scope-header .arrow.open { transform: rotate(90deg); }
.acc-scope-header .scope-name { font-size: 14px; font-weight: 700; color: #333; flex: 1; }
.acc-scope-header .scope-count { font-size: 11px; color: #999; background: #f0f0ec; padding: 2px 8px; border-radius: 10px; }
.acc-scope-body { max-height: 0; overflow: hidden; transition: max-height 0.35s ease; }
.acc-scope-body.open { max-height: 4000px; }

.acc-region { border-top: 1px solid #f0f0f0; }
.acc-region-header { display: flex; align-items: center; padding: 9px 18px 9px 36px; cursor: pointer; user-select: none; transition: background 0.15s; font-family: system-ui, sans-serif; }
.acc-region-header:hover { background: #fafaf5; }
.acc-region-header .arrow { width: 16px; height: 16px; display: flex; align-items: center; justify-content: center; font-size: 9px; color: #aaa; transition: transform 0.25s; margin-right: 8px; flex-shrink: 0; }
.acc-region-header .arrow.open { transform: rotate(90deg); }
.acc-region-header .region-name { font-size: 13px; font-weight: 600; color: #444; flex: 1; }
.acc-region-header .region-count { font-size: 10px; color: #aaa; }
.acc-region-body { max-height: 0; overflow: hidden; transition: max-height 0.3s ease; }
.acc-region-body.open { max-height: 3000px; }

.acc-article { padding: 8px 18px 8px 60px; border-top: 1px solid #f5f5f5; cursor: pointer; transition: background 0.15s; }
.acc-article:hover { background: #f8f8f4; }
.acc-article.selected { background: #eef4ff; border-left: 3px solid #4285f4; padding-left: 57px; }
.acc-article-row { display: flex; align-items: center; gap: 8px; }
.acc-article .badge { font-family: system-ui, sans-serif; font-size: 9px; font-weight: 700; text-transform: uppercase; padding: 2px 7px; border-radius: 3px; flex-shrink: 0; }
.badge.positive { background: #e6f4ea; color: #34a853; }
.badge.negative { background: #fce8e6; color: #ea4335; }
.badge.neutral { background: #f1f3f4; color: #888; }
.acc-article .art-title { font-size: 13px; line-height: 1.35; color: #333; flex: 1; }
.acc-article .art-date { font-family: system-ui, sans-serif; font-size: 10px; color: #aaa; flex-shrink: 0; }
.acc-article .art-opinion { max-height: 0; overflow: hidden; transition: max-height 0.3s ease, opacity 0.3s; opacity: 0; font-size: 12px; line-height: 1.5; color: #666; padding-left: 0; font-style: italic; }
.acc-article.expanded .art-opinion { max-height: 200px; opacity: 1; margin-top: 6px; }

/* ── Detail panel ── */
.detail-panel { background: #fff; border: 1px solid #e0e0e0; border-radius: 4px; position: sticky; top: 20px; align-self: start; }
.detail-panel .panel-header { font-family: system-ui, sans-serif; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #666; font-weight: 700; padding: 14px 20px 10px; border-bottom: 1px solid #eee; }
.detail-content { padding: 20px; transition: opacity 0.3s; }
.detail-content.fading { opacity: 0; }
.detail-empty { padding: 40px 20px; text-align: center; color: #bbb; font-family: system-ui, sans-serif; font-size: 13px; }
.detail-empty .icon { font-size: 32px; margin-bottom: 8px; }
.detail-title { font-size: 18px; line-height: 1.35; margin-bottom: 12px; }
.detail-meta { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; font-family: system-ui, sans-serif; font-size: 12px; color: #888; flex-wrap: wrap; }
.detail-meta .badge { font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 3px 9px; border-radius: 3px; }
.detail-opinion-label { font-family: system-ui, sans-serif; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: #999; font-weight: 700; margin-bottom: 6px; }
.detail-opinion { font-size: 14px; line-height: 1.65; color: #444; font-style: italic; border-left: 3px solid #dadce0; padding-left: 14px; }

/* ── Charts ── */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
.card { background: #fff; border: 1px solid #e0e0e0; border-radius: 4px; padding: 20px; }
.card h3 { font-family: system-ui, sans-serif; font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #666; margin-bottom: 14px; font-weight: 700; }
.card canvas { max-height: 220px; }

/* ── Footer ── */
.footer { text-align: center; padding: 20px; color: #999; font-size: 11px; font-family: system-ui, sans-serif; border-top: 1px solid #eee; margin-top: 28px; }
</style>
</head>
<body>

<div class="masthead">
  <h1>nonews</h1>
  <div class="edition">Panorama informativo de Mexico</div>
  <div class="dateline" id="genDate"></div>
</div>

<div class="filter-bar">
  <label>Rango de fechas</label>
  <div class="range-group">
    <input type="date" id="dateMin">
    <span class="range-sep">&mdash;</span>
    <input type="date" id="dateMax">
  </div>
  <div class="filter-count" id="filterCount"></div>
</div>

<div class="container">
  <!-- Hero summary -->
  <div class="hero">
    <h2 id="heroTitle">Panorama general</h2>
    <p id="heroText"></p>
    <div class="sentiment-bar"><div class="pos" id="barPos"></div><div class="neg" id="barNeg"></div><div class="neu" id="barNeu"></div></div>
    <div class="sentiment-legend"><span id="posLabel"></span><span id="negLabel"></span><span id="neuLabel"></span></div>
  </div>

  <!-- Main split: accordion + detail -->
  <div class="section-label">Explorar articulos</div>
  <div class="main-split">
    <div class="accordion-panel">
      <div class="panel-header">Jerarquia: Nacional / Internacional &rarr; Region &rarr; Articulo</div>
      <div id="accordionRoot"></div>
    </div>
    <div class="detail-panel">
      <div class="panel-header">Articulo seleccionado</div>
      <div id="detailBody">
        <div class="detail-empty">
          <div class="icon">&#128240;</div>
          <div>Selecciona un articulo del panel izquierdo para ver sus detalles</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Charts -->
  <hr class="section-rule">
  <div class="section-label">Visualizaciones</div>
  <div class="two-col">
    <div class="card"><h3>Sentimiento general</h3><canvas id="sentimentChart"></canvas></div>
    <div class="card"><h3>Regiones con mas cobertura</h3><canvas id="regionChart"></canvas></div>
  </div>
  <div class="two-col">
    <div class="card"><h3>Volumen diario</h3><canvas id="timelineChart"></canvas></div>
    <div class="card"><h3>Sentimiento por region (top 10)</h3><canvas id="sentRegionChart"></canvas></div>
  </div>
</div>

<div class="footer">Generado el <span id="genDate2"></span> &mdash; nonews</div>

<script>
const DATA = __DATA__;
const HIERARCHY_DATA = __HIERARCHY_ARTICLES__;

const HIERARCHY = HIERARCHY_DATA.hierarchy;
const DATE_RANGE = HIERARCHY_DATA.date_range;

/* ── State ── */
var currentMinDate = DATE_RANGE.min;
var currentMaxDate = DATE_RANGE.max;

/* ── Init date inputs ── */
var dateMinInput = document.getElementById('dateMin');
var dateMaxInput = document.getElementById('dateMax');
dateMinInput.value = DATE_RANGE.min;
dateMaxInput.value = DATE_RANGE.max;
dateMinInput.min = DATE_RANGE.min;
dateMinInput.max = DATE_RANGE.max;
dateMaxInput.min = DATE_RANGE.min;
dateMaxInput.max = DATE_RANGE.max;

/* ── Header ── */
document.getElementById('genDate').textContent = DATA.summary.generated_at;
document.getElementById('genDate2').textContent = DATA.summary.generated_at;

/* ── Helper: filter articles by date ── */
function articleInRange(dateStr) {
  if (!dateStr) return true;
  return dateStr >= currentMinDate && dateStr <= currentMaxDate;
}

function getFilteredCounts() {
  var total = 0, pos = 0, neg = 0, neu = 0;
  var branchKeys = ['national','international'];
  for (var bi = 0; bi < branchKeys.length; bi++) {
    var branch = HIERARCHY[branchKeys[bi]];
    var regionKeys = Object.keys(branch.regions);
    for (var ri = 0; ri < regionKeys.length; ri++) {
      var articles = branch.regions[regionKeys[ri]].articles;
      for (var ai = 0; ai < articles.length; ai++) {
        if (articleInRange(articles[ai].date)) {
          total++;
          if (articles[ai].sentiment === 'positive') pos++;
          else if (articles[ai].sentiment === 'negative') neg++;
          else neu++;
        }
      }
    }
  }
  return { total: total, pos: pos, neg: neg, neu: neu };
}

function updateHero() {
  var c = getFilteredCounts();
  var posPct = c.total ? Math.round(c.pos / c.total * 1000) / 10 : 0;
  var negPct = c.total ? Math.round(c.neg / c.total * 1000) / 10 : 0;
  var neuPct = c.total ? Math.round(c.neu / c.total * 1000) / 10 : 0;
  document.getElementById('heroTitle').textContent = c.total + ' articulos en el rango seleccionado';
  var dominant = posPct >= negPct ? 'positivo' : 'negativo';
  document.getElementById('heroText').textContent =
    'El ' + Math.max(posPct, negPct) + '% de las noticias tiene un tono ' + dominant + '.';
  document.getElementById('barPos').style.width = posPct + '%';
  document.getElementById('barNeg').style.width = negPct + '%';
  document.getElementById('barNeu').style.width = neuPct + '%';
  document.getElementById('posLabel').textContent = posPct + '% positivo';
  document.getElementById('negLabel').textContent = negPct + '% negativo';
  document.getElementById('neuLabel').textContent = neuPct + '% neutral';
  document.getElementById('filterCount').innerHTML = '<strong>' + c.total + '</strong> articulos filtrados';
}

/* ── Accordion rendering ── */
function buildAccordion() {
  var root = document.getElementById('accordionRoot');
  root.innerHTML = '';

  var scopeLabels = { national: 'Nacional', international: 'Internacional' };
  var branchKeys = ['national', 'international'];

  for (var bi = 0; bi < branchKeys.length; bi++) {
    var branchKey = branchKeys[bi];
    var branch = HIERARCHY[branchKey];
    var scopeEl = document.createElement('div');
    scopeEl.className = 'acc-scope';

    // Count filtered articles in this scope
    var scopeCount = 0;
    var rKeys = Object.keys(branch.regions);
    for (var ri = 0; ri < rKeys.length; ri++) {
      var arts = branch.regions[rKeys[ri]].articles;
      for (var ai = 0; ai < arts.length; ai++) {
        if (articleInRange(arts[ai].date)) scopeCount++;
      }
    }

    // Scope header
    var header = document.createElement('div');
    header.className = 'acc-scope-header';
    header.innerHTML = '<span class="arrow">&#9654;</span><span class="scope-name">' + scopeLabels[branchKey] + '</span><span class="scope-count">' + scopeCount + '</span>';
    scopeEl.appendChild(header);

    // Scope body
    var body = document.createElement('div');
    body.className = 'acc-scope-body';

    // Regions sorted by filtered count
    var regionEntries = [];
    for (var ri2 = 0; ri2 < rKeys.length; ri2++) {
      var rName = rKeys[ri2];
      var rData = branch.regions[rName];
      var filtered = [];
      for (var ai2 = 0; ai2 < rData.articles.length; ai2++) {
        if (articleInRange(rData.articles[ai2].date)) filtered.push(rData.articles[ai2]);
      }
      regionEntries.push([rName, rData, filtered.length, filtered]);
    }
    regionEntries.sort(function(a, b) { return b[2] - a[2]; });

    for (var re = 0; re < regionEntries.length; re++) {
      var regionName = regionEntries[re][0];
      var regionData = regionEntries[re][1];
      var filteredCount = regionEntries[re][2];
      var filteredArticles = regionEntries[re][3];

      if (filteredCount === 0) continue;

      var regionEl = document.createElement('div');
      regionEl.className = 'acc-region';

      var rHeader = document.createElement('div');
      rHeader.className = 'acc-region-header';
      rHeader.innerHTML = '<span class="arrow">&#9654;</span><span class="region-name">' + regionName + '</span><span class="region-count">' + filteredCount + '</span>';
      regionEl.appendChild(rHeader);

      var rBody = document.createElement('div');
      rBody.className = 'acc-region-body';

      for (var fa = 0; fa < filteredArticles.length; fa++) {
        (function(art) {
          var artEl = document.createElement('div');
          artEl.className = 'acc-article';

          var sentLabel = art.sentiment === 'positive' ? 'pos' : art.sentiment === 'negative' ? 'neg' : 'neu';
          artEl.innerHTML =
            '<div class="acc-article-row">' +
              '<span class="badge ' + art.sentiment + '">' + sentLabel + '</span>' +
              '<span class="art-title">' + (art.title || '') + '</span>' +
              '<span class="art-date">' + (art.date ? art.date.slice(5) : '') + '</span>' +
            '</div>' +
            '<div class="art-opinion">' + (art.opinion || 'Sin opinion disponible.') + '</div>';

          artEl.addEventListener('click', function(e) {
            e.stopPropagation();
            // Toggle inline expansion
            var wasExpanded = artEl.classList.contains('expanded');
            var allExpanded = root.querySelectorAll('.acc-article.expanded');
            for (var x = 0; x < allExpanded.length; x++) allExpanded[x].classList.remove('expanded');
            if (!wasExpanded) artEl.classList.add('expanded');
            // Select for detail panel
            var allSelected = root.querySelectorAll('.acc-article.selected');
            for (var y = 0; y < allSelected.length; y++) allSelected[y].classList.remove('selected');
            artEl.classList.add('selected');
            showDetail(art);
          });

          rBody.appendChild(artEl);
        })(filteredArticles[fa]);
      }

      regionEl.appendChild(rBody);

      // Region toggle
      (function(rHeaderEl, rBodyEl) {
        rHeaderEl.addEventListener('click', function() {
          var arrow = rHeaderEl.querySelector('.arrow');
          var isOpen = rBodyEl.classList.contains('open');
          if (isOpen) {
            rBodyEl.classList.remove('open');
            arrow.classList.remove('open');
          } else {
            rBodyEl.classList.add('open');
            arrow.classList.add('open');
          }
        });
      })(rHeader, rBody);

      body.appendChild(regionEl);
    }

    scopeEl.appendChild(body);

    // Scope toggle
    (function(headerEl, bodyEl) {
      headerEl.addEventListener('click', function() {
        var arrow = headerEl.querySelector('.arrow');
        var isOpen = bodyEl.classList.contains('open');
        if (isOpen) {
          bodyEl.classList.remove('open');
          arrow.classList.remove('open');
        } else {
          bodyEl.classList.add('open');
          arrow.classList.add('open');
        }
      });
    })(header, body);

    root.appendChild(scopeEl);
  }
}

/* ── Detail panel ── */
function showDetail(art) {
  var body = document.getElementById('detailBody');
  body.classList.add('fading');
  setTimeout(function() {
    var sentLabel = art.sentiment === 'positive' ? 'Positivo' : art.sentiment === 'negative' ? 'Negativo' : 'Neutral';
    var regionDisplay = art.region === 'international' ? 'Internacional' : art.region;
    body.innerHTML =
      '<div class="detail-content">' +
        '<div class="detail-title">' + (art.title || '') + '</div>' +
        '<div class="detail-meta">' +
          '<span class="badge ' + art.sentiment + '">' + sentLabel + '</span>' +
          '<span>' + regionDisplay + '</span>' +
          '<span>' + (art.date || '') + '</span>' +
        '</div>' +
        '<div class="detail-opinion-label">Opinion</div>' +
        '<div class="detail-opinion">' + (art.opinion || 'Sin opinion disponible.') + '</div>' +
      '</div>';
    body.classList.remove('fading');
  }, 200);
}

/* ── Charts ── */
var SENTIMENT_COLORS = ['#34a853', '#ea4335', '#dadce0'];
var sentimentChart, regionChart, timelineChart, sentRegionChart;

function computeFilteredData() {
  var sentiments = { positive: 0, negative: 0, neutral: 0 };
  var regions = {};
  var timeline = {};
  var sentByRegion = {};

  var branchKeys = ['national', 'international'];
  for (var bi = 0; bi < branchKeys.length; bi++) {
    var branch = HIERARCHY[branchKeys[bi]];
    var rKeys = Object.keys(branch.regions);
    for (var ri = 0; ri < rKeys.length; ri++) {
      var articles = branch.regions[rKeys[ri]].articles;
      for (var ai = 0; ai < articles.length; ai++) {
        var art = articles[ai];
        if (!articleInRange(art.date)) continue;
        sentiments[art.sentiment]++;
        regions[art.region] = (regions[art.region] || 0) + 1;
        if (art.date) timeline[art.date] = (timeline[art.date] || 0) + 1;
        if (!sentByRegion[art.region]) sentByRegion[art.region] = { positive: 0, negative: 0, neutral: 0 };
        sentByRegion[art.region][art.sentiment]++;
      }
    }
  }

  var sentLabels = ['positive', 'negative', 'neutral'];
  var sentValues = [sentiments.positive, sentiments.negative, sentiments.neutral];

  var sortedRegions = Object.entries(regions).sort(function(a, b) { return b[1] - a[1]; }).slice(0, 15);
  var sortedDays = Object.keys(timeline).sort();

  var sortedSentRegions = Object.entries(sentByRegion).sort(function(a, b) {
    var ta = b[1].positive + b[1].negative + b[1].neutral;
    var tb = a[1].positive + a[1].negative + a[1].neutral;
    return ta - tb;
  }).slice(0, 10);

  return {
    sentiment: { labels: sentLabels, values: sentValues },
    region: { labels: sortedRegions.map(function(r) { return r[0]; }), values: sortedRegions.map(function(r) { return r[1]; }) },
    timeline: { labels: sortedDays, values: sortedDays.map(function(d) { return timeline[d]; }) },
    sentRegion: {
      labels: sortedSentRegions.map(function(r) { return r[0]; }),
      positive: sortedSentRegions.map(function(r) { return r[1].positive; }),
      negative: sortedSentRegions.map(function(r) { return r[1].negative; }),
      neutral: sortedSentRegions.map(function(r) { return r[1].neutral; }),
    }
  };
}

function initCharts() {
  var fd = computeFilteredData();

  sentimentChart = new Chart(document.getElementById('sentimentChart'), {
    type: 'pie',
    data: { labels: ['Positivo','Negativo','Neutral'], datasets: [{ data: fd.sentiment.values, backgroundColor: SENTIMENT_COLORS }] },
    options: { plugins: { legend: { position: 'bottom' } } }
  });

  regionChart = new Chart(document.getElementById('regionChart'), {
    type: 'bar',
    data: { labels: fd.region.labels, datasets: [{ data: fd.region.values, backgroundColor: '#4285f4' }] },
    options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { grid: { display: false } } } }
  });

  timelineChart = new Chart(document.getElementById('timelineChart'), {
    type: 'bar',
    data: { labels: fd.timeline.labels.map(function(d) { return d.slice(5); }), datasets: [{ data: fd.timeline.values, backgroundColor: '#4285f4' }] },
    options: { plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 12 } }, y: { grid: { color: '#eee' } } } }
  });

  sentRegionChart = new Chart(document.getElementById('sentRegionChart'), {
    type: 'bar',
    data: {
      labels: fd.sentRegion.labels,
      datasets: [
        { label: 'Positivo', data: fd.sentRegion.positive, backgroundColor: '#34a853' },
        { label: 'Negativo', data: fd.sentRegion.negative, backgroundColor: '#ea4335' },
        { label: 'Neutral', data: fd.sentRegion.neutral, backgroundColor: '#dadce0' },
      ]
    },
    options: { plugins: { legend: { labels: { font: { size: 11 } } } }, scales: { x: { stacked: true, grid: { display: false }, ticks: { font: { size: 10 } } }, y: { stacked: true, grid: { color: '#eee' } } } }
  });
}

function updateCharts() {
  var fd = computeFilteredData();

  sentimentChart.data.datasets[0].data = fd.sentiment.values;
  sentimentChart.update();

  regionChart.data.labels = fd.region.labels;
  regionChart.data.datasets[0].data = fd.region.values;
  regionChart.update();

  timelineChart.data.labels = fd.timeline.labels.map(function(d) { return d.slice(5); });
  timelineChart.data.datasets[0].data = fd.timeline.values;
  timelineChart.update();

  sentRegionChart.data.labels = fd.sentRegion.labels;
  sentRegionChart.data.datasets[0].data = fd.sentRegion.positive;
  sentRegionChart.data.datasets[1].data = fd.sentRegion.negative;
  sentRegionChart.data.datasets[2].data = fd.sentRegion.neutral;
  sentRegionChart.update();
}

/* ── Date filter handlers ── */
function onDateChange() {
  currentMinDate = dateMinInput.value || DATE_RANGE.min;
  currentMaxDate = dateMaxInput.value || DATE_RANGE.max;
  if (currentMinDate > currentMaxDate) {
    var tmp = currentMinDate;
    currentMinDate = currentMaxDate;
    currentMaxDate = tmp;
  }
  updateHero();
  buildAccordion();
  updateCharts();
}
dateMinInput.addEventListener('input', onDateChange);
dateMaxInput.addEventListener('input', onDateChange);

/* ── Boot ── */
updateHero();
buildAccordion();
initCharts();
</script>
</body>
</html>"""


def generate(template: str = "D3", output_path: str | None = None) -> str:
    from nonews.report import build_hierarchy_data, build_sidebar_data, build_hierarchy_articles_data

    data = build_report_data(include_fake=False)
    hierarchy = build_hierarchy_data(include_fake=False)
    sidebar = build_sidebar_data(include_fake=False)
    hierarchy_articles = build_hierarchy_articles_data(include_fake=False)
    DATA_DIR.mkdir(exist_ok=True)

    if output_path:
        default_output = Path(output_path)
    else:
        default_output = DATA_DIR / "report.html"

    templates = {
        "A": (TEMPLATE_A, DATA_DIR / "report_a.html"),
        "B": (TEMPLATE_B, DATA_DIR / "report_b.html"),
        "C": (TEMPLATE_C, DATA_DIR / "report_c.html"),
        "D": (TEMPLATE_D, DATA_DIR / "report_d.html"),
        "D1": (TEMPLATE_D1, DATA_DIR / "report_d1.html"),
        "D2": (TEMPLATE_D2, DATA_DIR / "report_d2.html"),
        "D3": (TEMPLATE_D3, default_output),
    }

    if template != "all":
        templates = {template: templates[template]}

    for name, (html_template, output_path) in templates.items():
        tpl_data = data
        if name == "D":
            # Template D shows only 10 articles and 15 timeline days
            tpl_data = dict(data)
            tpl_data["top_articles"] = data["top_articles"][:10]
            tpl_data["timeline"] = {
                "labels": data["timeline"]["labels"][:15],
                "values": data["timeline"]["values"][:15],
            }
        html = _inject_data(html_template, tpl_data)
        if name == "D":
            html = html.replace("__HIERARCHY__", json.dumps(hierarchy, ensure_ascii=False))
        if name in ("D1", "D3"):
            html = html.replace("__SIDEBAR__", json.dumps(sidebar, ensure_ascii=False))
        if name == "D2":
            html = html.replace("__HIERARCHY_ARTICLES__", json.dumps(hierarchy_articles, ensure_ascii=False))
        output_path.write_text(html, encoding='utf-8')
        print(f"Generated {output_path}")

    return str(default_output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", choices=["A", "B", "C", "D", "D1", "D2", "D3", "all"], default="D3")
    parser.add_argument("--output", "-o", default=None, help="Output file path")
    args = parser.parse_args()
    generate(args.template, args.output)
