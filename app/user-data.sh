#!/bin/bash
# Script d'installation automatique pour EC2
# Projet DIGITRANS-CM - Module BI

set -e

apt update -y
apt install -y python3-pip

pip3 install flask flask-cors gunicorn

mkdir -p /opt/bi-app

cat > /opt/bi-app/main.py << 'EOF'
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>AGROCAM BI Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        *{margin:0;padding:0;box-sizing:border-box;}
        body{font-family:Arial;background:linear-gradient(135deg,#1a1a2e,#16213e);padding:20px;}
        .container{max-width:1200px;margin:0 auto;}
        .header{background:white;border-radius:20px;padding:20px;margin-bottom:20px;text-align:center;}
        .kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-bottom:20px;}
        .kpi-card{background:white;border-radius:15px;padding:20px;text-align:center;}
        .kpi-value{font-size:28px;font-weight:bold;color:#1a1a2e;}
        .chart-card{background:white;border-radius:15px;padding:20px;margin-bottom:20px;}
        canvas{max-height:300px;}
        @media(max-width:768px){.kpi-grid{grid-template-columns:repeat(2,1fr);}}
    </style>
</head>
<body>
<div class=container>
<div class=header><h1>AGROCAM - Business Intelligence Dashboard</h1><p>Module BI - Projet DIGITRANS-CM</p></div>
<div class=kpi-grid id=kpis></div>
<div class=chart-card><canvas id=salesChart></canvas></div>
<div class=chart-card><canvas id=categoryChart></canvas></div>
</div>
<script>
async function loadData(){
    let kpi=await fetch('/api/kpi').then(r=>r.json());
    document.getElementById('kpis').innerHTML=`
        <div class=kpi-card><h3>CA Total</h3><div class=kpi-value>${(kpi.total_revenue/1e6).toFixed(1)}M FCFA</div></div>
        <div class=kpi-card><h3>Clients</h3><div class=kpi-value>${kpi.unique_customers}</div></div>
        <div class=kpi-card><h3>Panier moyen</h3><div class=kpi-value>${(kpi.avg_basket/1000).toFixed(0)}K FCFA</div></div>
        <div class=kpi-card><h3>Prevision</h3><div class=kpi-value>${(kpi.forecast/1e6).toFixed(1)}M FCFA</div></div>`;
    let sales=await fetch('/api/sales').then(r=>r.json());
    new Chart(document.getElementById('salesChart'),{type:'line',data:{labels:sales.labels,datasets:[{label:'Ventes FCFA',data:sales.values,borderColor:'#1a1a2e',fill:false}]}});
    let cat=await fetch('/api/categories').then(r=>r.json());
    new Chart(document.getElementById('categoryChart'),{type:'doughnut',data:{labels:cat.labels,datasets:[{data:cat.values,backgroundColor:['#1a1a2e','#16213e','#0f3460','#e94560']}]}});
}
loadData();
setInterval(loadData,30000);
</script>
</body>
</html>
'''

@app.route('/')
def dashboard():
    return render_template_string(HTML)

@app.route('/api/kpi')
def kpi():
    return {
        'total_revenue': 45280000,
        'unique_customers': 1247,
        'avg_basket': 36320,
        'forecast': 15850000
    }

@app.route('/api/sales')
def sales():
    return {
        'labels': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
        'values': [3200000, 4100000, 3800000, 5200000, 6800000, 4900000, 3500000]
    }

@app.route('/api/categories')
def categories():
    return {
        'labels': ['Cafe', 'Cacao', 'Alimentaire', 'Restaurant'],
        'values': [28500000, 34200000, 19800000, 15600000]
    }

@app.route('/health')
def health():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
EOF

cat > /etc/systemd/system/bi-app.service << EOF
[Unit]
Description=BI Application Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/bi-app
ExecStart=/usr/local/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable bi-app
systemctl start bi-app

echo "Deploiement termine - BI Dashboard accessible sur le port 5000"