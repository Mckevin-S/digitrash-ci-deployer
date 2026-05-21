#!/usr/bin/env python3
"""
Module BI - Dashboard AGROCAM
Projet DIGITRANS-CM
Auteur: CAMTECH SOLUTIONS
"""

from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics
import json
import os
import psycopg2
import redis
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)
metrics = PrometheusMetrics(app)

# Configuration depuis variables d'environnement
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'bidb')
DB_USER = os.getenv('DB_USER', 'bi_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Connexion Redis (cache)
try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except:
    REDIS_AVAILABLE = False

def get_db_connection():
    """Connexion à PostgreSQL"""
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

# Dashboard HTML intégré
HTML_DASHBOARD = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AGROCAM - Business Intelligence Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #1a1a2e, #16213e); min-height: 100vh; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: white; border-radius: 20px; padding: 25px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .logo-section h1 { color: #1a1a2e; font-size: 1.8rem; }
        .logo-section p { color: #666; margin-top: 5px; }
        .date-time { color: #666; font-size: 0.9rem; }
        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 25px; }
        .kpi-card { background: white; border-radius: 20px; padding: 20px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: transform 0.3s; }
        .kpi-card:hover { transform: translateY(-5px); }
        .kpi-icon { width: 60px; height: 60px; background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 15px; display: flex; align-items: center; justify-content: center; }
        .kpi-icon i { font-size: 28px; color: white; }
        .kpi-content h3 { font-size: 0.85rem; color: #666; margin-bottom: 5px; }
        .kpi-value { font-size: 1.8rem; font-weight: bold; color: #1a1a2e; }
        .kpi-trend { font-size: 0.75rem; margin-top: 5px; display: inline-block; padding: 2px 8px; border-radius: 20px; }
        .trend-positive { background: #e6f7e6; color: #28a745; }
        .trend-negative { background: #ffe6e6; color: #dc3545; }
        .chart-card { background: white; border-radius: 20px; padding: 20px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .chart-header h3 i { color: #1a1a2e; margin-right: 10px; }
        .period-selector { padding: 8px 15px; border: 1px solid #ddd; border-radius: 10px; background: white; cursor: pointer; }
        .data-table { background: white; border-radius: 20px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .table-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 15px; }
        .search-input { padding: 10px 15px; border: 1px solid #ddd; border-radius: 10px; width: 250px; }
        .export-btn { padding: 10px 20px; background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; border: none; border-radius: 10px; cursor: pointer; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f5f5f5; font-weight: 600; }
        tr:hover { background: #f9f9f9; }
        @media (max-width: 768px) { .kpi-grid { grid-template-columns: repeat(2,1fr); } .header { flex-direction: column; gap: 15px; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo-section">
                <h1><i class="fas fa-chart-line" style="color: #1a1a2e;"></i> AGROCAM - BI Dashboard</h1>
                <p>Module Business Intelligence | Projet DIGITRANS-CM</p>
            </div>
            <div class="date-time" id="currentDateTime"></div>
        </div>
        <div class="kpi-grid" id="kpis">
            <div class="kpi-card"><div class="kpi-icon"><i class="fas fa-spinner fa-spin"></i></div><div class="kpi-content"><h3>Chargement...</h3><div class="kpi-value">---</div></div></div>
        </div>
        <div class="chart-card">
            <div class="chart-header"><h3><i class="fas fa-chart-line"></i> Évolution des ventes</h3><select id="periodSelect" class="period-selector" onchange="loadSalesData()"><option value="week">7 jours</option><option value="month" selected="selected">30 jours</option><option value="year">12 mois</option></select></div>
            <canvas id="salesChart" height="300"></canvas>
        </div>
        <div class="chart-card">
            <div class="chart-header"><h3><i class="fas fa-chart-pie"></i> Répartition par catégorie</h3></div>
            <canvas id="categoryChart" height="300"></canvas>
        </div>
        <div class="data-table">
            <div class="table-header"><h3><i class="fas fa-table"></i> Détail des ventes</h3><div><input type="text" id="searchInput" class="search-input" placeholder="Rechercher..." onkeyup="filterTable()"><button class="export-btn" onclick="exportToCSV()"><i class="fas fa-download"></i> Export CSV</button></div></div>
            <div style="overflow-x: auto;"><table id="salesTable"><thead><tr><th>Date</th><th>Produit</th><th>Catégorie</th><th>Quantité</th><th>Montant (FCFA)</th><th>Région</th></tr></thead><tbody id="tableBody"><tr><td colspan="6">Chargement...</td></tr></tbody></table></div>
        </div>
    </div>
    <script>
        let salesChart, categoryChart;
        function updateDateTime() { document.getElementById('currentDateTime').innerHTML = new Date().toLocaleString('fr-FR'); }
        setInterval(updateDateTime, 1000);
        updateDateTime();
        
        async function loadKPIs() {
            try {
                let res = await fetch('/api/kpi');
                let data = await res.json();
                document.getElementById('kpis').innerHTML = `
                    <div class="kpi-card"><div class="kpi-icon"><i class="fas fa-chart-line"></i></div><div class="kpi-content"><h3>CHIFFRE D'AFFAIRES</h3><div class="kpi-value">${(data.total_revenue/1e6).toFixed(1)}M FCFA</div><span class="kpi-trend trend-positive"><i class="fas fa-arrow-up"></i> +12%</span></div></div>
                    <div class="kpi-card"><div class="kpi-icon"><i class="fas fa-users"></i></div><div class="kpi-content"><h3>CLIENTS UNIQUES</h3><div class="kpi-value">${data.unique_customers.toLocaleString()}</div><span class="kpi-trend trend-positive"><i class="fas fa-arrow-up"></i> +5%</span></div></div>
                    <div class="kpi-card"><div class="kpi-icon"><i class="fas fa-shopping-cart"></i></div><div class="kpi-content"><h3>PANIER MOYEN</h3><div class="kpi-value">${(data.avg_basket/1000).toFixed(0)}K FCFA</div><span class="kpi-trend trend-positive">Stable</span></div></div>
                    <div class="kpi-card"><div class="kpi-icon"><i class="fas fa-chart-line"></i></div><div class="kpi-content"><h3>PRÉVISION (7j)</h3><div class="kpi-value">${(data.forecast/1e6).toFixed(1)}M FCFA</div><span class="kpi-trend trend-positive"><i class="fas fa-chart-line"></i> Estimation</span></div></div>
                `;
            } catch(e) { console.error('Erreur KPI:', e); }
        }
        
        async function loadSalesData() {
            let period = document.getElementById('periodSelect').value;
            try {
                let res = await fetch(`/api/sales?period=${period}`);
                let data = await res.json();
                if (salesChart) salesChart.destroy();
                let ctx = document.getElementById('salesChart').getContext('2d');
                salesChart = new Chart(ctx, { type: 'line', data: { labels: data.labels, datasets: [{ label: 'Chiffre d\'affaires (FCFA)', data: data.values, borderColor: '#1a1a2e', backgroundColor: 'rgba(26,26,46,0.1)', fill: true, tension: 0.4 }] }, options: { responsive: true, maintainAspectRatio: true, plugins: { tooltip: { callbacks: { label: (ctx) => `${ctx.raw.toLocaleString()} FCFA` } } } } });
            } catch(e) { console.error('Erreur Sales:', e); }
        }
        
        async function loadCategoryData() {
            try {
                let res = await fetch('/api/categories');
                let data = await res.json();
                if (categoryChart) categoryChart.destroy();
                let ctx = document.getElementById('categoryChart').getContext('2d');
                categoryChart = new Chart(ctx, { type: 'doughnut', data: { labels: data.labels, datasets: [{ data: data.values, backgroundColor: ['#1a1a2e', '#16213e', '#0f3460', '#e94560'] }] }, options: { responsive: true, plugins: { legend: { position: 'bottom' }, tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${(ctx.raw/1e6).toFixed(1)}M FCFA` } } } } });
            } catch(e) { console.error('Erreur Catégories:', e); }
        }
        
        async function loadTable() {
            try {
                let res = await fetch('/api/transactions');
                let data = await res.json();
                let html = data.map(t => `<tr><td>${t.date}</td><td>${t.product}</td><td>${t.category}</td><td>${t.qty}</td><td>${(t.amount/1e6).toFixed(2)}M</td><td>${t.region}</td></tr>`).join('');
                document.getElementById('tableBody').innerHTML = html || '<tr><td colspan="6">Aucune donnée</td></tr>';
            } catch(e) { console.error('Erreur Table:', e); }
        }
        
        function filterTable() { let input = document.getElementById('searchInput').value.toLowerCase(); let rows = document.querySelectorAll('#tableBody tr'); rows.forEach(row => { row.style.display = row.innerText.toLowerCase().includes(input) ? '' : 'none'; }); }
        
        function exportToCSV() { let rows = document.querySelectorAll('#tableBody tr'); let csv = 'Date,Produit,Catégorie,Quantité,Montant,Région\\n'; rows.forEach(row => { if (row.style.display !== 'none') { let cells = row.querySelectorAll('td'); csv += Array.from(cells).map(c => c.innerText).join(',') + '\\n'; } }); let blob = new Blob([csv], { type: 'text/csv' }); let a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `ventes_${new Date().toISOString().split('T')[0]}.csv`; a.click(); }
        
        loadKPIs(); loadSalesData(); loadCategoryData(); loadTable();
        setInterval(() => { loadKPIs(); loadTable(); }, 30000);
    </script>
</body>
</html>
'''

@app.route('/')
def dashboard():
    """Page d'accueil - Dashboard BI"""
    return render_template_string(HTML_DASHBOARD)

@app.route('/health')
def health():
    """Health check pour ELB"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'services': {
            'database': 'connected' if DB_HOST != 'localhost' else 'mock',
            'redis': 'connected' if REDIS_AVAILABLE else 'disabled'
        }
    })

@app.route('/api/kpi')
def get_kpi():
    """Indicateurs clés de performance"""
    # Mock data pour démonstration
    return jsonify({
        'total_revenue': 45280000,
        'unique_customers': 1247,
        'avg_basket': 36320,
        'forecast': 15850000,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/sales')
def get_sales():
    """Ventes par période"""
    period = request.args.get('period', 'month')
    data = {
        'week': {'labels': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'], 'values': [3200000, 4100000, 3800000, 5200000, 6800000, 4900000, 3500000]},
        'month': {'labels': ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4'], 'values': [18500000, 21200000, 19800000, 24500000]},
        'year': {'labels': ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'], 'values': [15200000, 16800000, 18500000, 19200000, 21000000, 22500000, 23800000, 24500000, 25200000, 26800000, 27500000, 29000000]}
    }
    return jsonify(data.get(period, data['month']))

@app.route('/api/categories')
def get_categories():
    """Ventes par catégorie"""
    return jsonify({
        'labels': ['Café', 'Cacao', 'Alimentaire', 'Restaurant'],
        'values': [28500000, 34200000, 19800000, 15600000]
    })

@app.route('/api/transactions')
def get_transactions():
    """Liste des transactions récentes"""
    return jsonify([
        {'date': '2026-05-21', 'product': 'Café Arabica', 'category': 'Café', 'qty': 450, 'amount': 2250000, 'region': 'Douala'},
        {'date': '2026-05-20', 'product': 'Cacao Premium', 'category': 'Cacao', 'qty': 320, 'amount': 3200000, 'region': 'Yaoundé'},
        {'date': '2026-05-20', 'product': 'Menu SavoirManger', 'category': 'Restaurant', 'qty': 890, 'amount': 4450000, 'region': 'Douala'},
        {'date': '2026-05-19', 'product': 'Café Robusta', 'category': 'Café', 'qty': 280, 'amount': 1400000, 'region': 'Bafoussam'},
        {'date': '2026-05-19', 'product': 'Beurre de Cacao', 'category': 'Cacao', 'qty': 150, 'amount': 2250000, 'region': 'Douala'}
    ])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)