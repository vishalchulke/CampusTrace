"""
============================================================
  CAMPUS LOST & FOUND MANAGEMENT SYSTEM
  Single-file Python Flask Application
  Database: SQLite (drop-in replacement for MySQL syntax)
  
  HOW TO RUN:
    pip install flask
    python lost_and_found.py
  
  Then open: http://localhost:5000
  
  Admin Login:
    Username: admin
    Password: admin123
  
  Demo Student Login:
    Username: student1
    Password: pass123
============================================================
"""

from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
import sqlite3, hashlib, os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "campus_lnf_secret_2024"

DB_PATH = "lost_found.db"

# ─────────────────────────────────────────────
#  DATABASE SETUP
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT UNIQUE NOT NULL,
            password  TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email     TEXT,
            role      TEXT DEFAULT 'student',
            created   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            type         TEXT NOT NULL,          -- 'lost' or 'found'
            category     TEXT NOT NULL,
            item_name    TEXT NOT NULL,
            description  TEXT,
            brand        TEXT,
            color        TEXT,
            location     TEXT NOT NULL,
            date_reported TEXT NOT NULL,
            date_lost_found TEXT,
            contact_name TEXT NOT NULL,
            contact_email TEXT,
            contact_phone TEXT,
            status       TEXT DEFAULT 'open',   -- open | claimed | closed
            user_id      INTEGER,
            created      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS claims (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id    INTEGER NOT NULL,
            user_id    INTEGER NOT NULL,
            message    TEXT,
            status     TEXT DEFAULT 'pending',  -- pending | approved | rejected
            created    TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(item_id) REFERENCES items(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)

    # seed admin
    c.execute("SELECT id FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users(username,password,full_name,email,role) VALUES(?,?,?,?,?)",
                  ('admin', hash_pw('admin123'), 'System Admin', 'admin@college.edu', 'admin'))

    # seed demo student
    c.execute("SELECT id FROM users WHERE username='student1'")
    if not c.fetchone():
        c.execute("INSERT INTO users(username,password,full_name,email,role) VALUES(?,?,?,?,?)",
                  ('student1', hash_pw('pass123'), 'Alex Johnson', 'alex@college.edu', 'student'))

    # seed sample items
    c.execute("SELECT COUNT(*) FROM items")
    if c.fetchone()[0] == 0:
        samples = [
            ('lost','Mobile Phone','Samsung Galaxy S21','Black Samsung phone with cracked screen protector','Samsung','Black','Library - 2nd Floor','2024-01-15','2024-01-14','Alex Johnson','alex@college.edu','9876543210','open',2),
            ('found','Earphones','JBL Wireless Earbuds','White earbuds found near cafeteria entrance','JBL','White','Cafeteria','2024-01-16','2024-01-16','Security Office','security@college.edu','0000','open',None),
            ('lost','Charger','MacBook Charger 65W','Apple USB-C charger, white cable','Apple','White','Computer Lab - Room 204','2024-01-17','2024-01-17','Priya Singh','priya@college.edu','9123456780','open',None),
            ('found','USB Drive','SanDisk 32GB USB','Orange USB drive with no label','SanDisk','Orange','Main Gate','2024-01-18','2024-01-18','Gate Security','gate@college.edu','0001','claimed',None),
            ('lost','Smart Watch','Noise ColorFit Pro','Black smartwatch, no strap scratches','Noise','Black','Gymnasium','2024-01-19','2024-01-18','Rahul Kumar','rahul@college.edu','9988776655','open',None),
            ('found','Calculator','Casio FX-991','Scientific calculator found on bench','Casio','Black/Blue','Block-B Corridor','2024-01-20','2024-01-20','Dept Office','dept@college.edu','0002','open',None),
        ]
        c.executemany("""INSERT INTO items(type,category,item_name,description,brand,color,location,
                         date_reported,date_lost_found,contact_name,contact_email,contact_phone,status,user_id)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", samples)

    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
#  AUTH DECORATORS
# ─────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────────
#  SHARED HTML TEMPLATE
# ─────────────────────────────────────────────
BASE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CampusTrace — Lost & Found</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
<style>
/* ── RESET & BASE ── */
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0c10;
  --surface:#111318;
  --card:#161a22;
  --border:#1e2330;
  --accent:#f0a500;
  --accent2:#e05c3a;
  --green:#2dce7a;
  --red:#e05c3a;
  --blue:#4da6ff;
  --purple:#9b6dff;
  --text:#e8eaf0;
  --muted:#6b7280;
  --radius:14px;
  --shadow:0 8px 32px rgba(0,0,0,.45);
}
html{scroll-behavior:smooth}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;
  background-image:radial-gradient(ellipse 80% 50% at 50% -20%,rgba(240,165,0,.08),transparent);
}
/* ── NAV ── */
nav{position:sticky;top:0;z-index:100;background:rgba(10,12,16,.85);backdrop-filter:blur(18px);
  border-bottom:1px solid var(--border);padding:0 2rem;display:flex;align-items:center;
  justify-content:space-between;height:64px;}
.nav-brand{font-family:'Syne',sans-serif;font-weight:800;font-size:1.25rem;letter-spacing:-.02em;
  color:var(--text);text-decoration:none;display:flex;align-items:center;gap:.5rem;}
.nav-brand span{color:var(--accent)}
.nav-links{display:flex;align-items:center;gap:.25rem;}
.nav-links a{color:var(--muted);text-decoration:none;padding:.45rem .85rem;border-radius:8px;
  font-size:.9rem;font-weight:500;transition:all .2s;}
.nav-links a:hover,.nav-links a.active{color:var(--text);background:var(--border);}
.nav-links a.btn-accent{background:var(--accent);color:#000;font-weight:600;}
.nav-links a.btn-accent:hover{background:#f5b830;}
.badge{display:inline-flex;align-items:center;justify-content:center;width:18px;height:18px;
  border-radius:50%;background:var(--accent2);color:#fff;font-size:.65rem;font-weight:700;margin-left:4px;}
/* ── LAYOUT ── */
.page{max-width:1200px;margin:0 auto;padding:2.5rem 1.5rem;}
.page-sm{max-width:520px;margin:0 auto;padding:2.5rem 1.5rem;}
/* ── HERO ── */
.hero{text-align:center;padding:4rem 1rem 3rem;position:relative;}
.hero-eyebrow{display:inline-flex;align-items:center;gap:.5rem;background:rgba(240,165,0,.1);
  color:var(--accent);border:1px solid rgba(240,165,0,.25);border-radius:99px;
  padding:.35rem 1rem;font-size:.8rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin-bottom:1.5rem;}
.hero h1{font-family:'Syne',sans-serif;font-size:clamp(2.2rem,5vw,3.8rem);font-weight:800;
  line-height:1.1;letter-spacing:-.03em;margin-bottom:1.2rem;}
.hero h1 em{color:var(--accent);font-style:normal;}
.hero p{color:var(--muted);font-size:1.05rem;max-width:520px;margin:0 auto 2.5rem;line-height:1.65;}
.hero-actions{display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;}
/* ── STATS BAR ── */
.stats-bar{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);
  border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;margin-bottom:3rem;}
.stat-cell{background:var(--card);padding:1.4rem;text-align:center;}
.stat-num{font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:var(--accent);}
.stat-lbl{font-size:.8rem;color:var(--muted);font-weight:500;margin-top:.2rem;}
/* ── CARDS ── */
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  padding:1.6rem;transition:border-color .2s,transform .2s;}
.card:hover{border-color:rgba(240,165,0,.3);transform:translateY(-2px);}
.card-grid{display:grid;gap:1.25rem;}
.card-grid.cols-2{grid-template-columns:repeat(auto-fill,minmax(340px,1fr));}
.card-grid.cols-3{grid-template-columns:repeat(auto-fill,minmax(260px,1fr));}
/* ITEM CARD */
.item-card{position:relative;display:flex;flex-direction:column;gap:.8rem;}
.item-card .type-badge{position:absolute;top:1.2rem;right:1.2rem;}
.item-meta{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;}
.chip{display:inline-flex;align-items:center;gap:.3rem;padding:.25rem .65rem;border-radius:6px;
  font-size:.75rem;font-weight:600;letter-spacing:.03em;}
.chip-lost{background:rgba(224,92,58,.15);color:#f08060;}
.chip-found{background:rgba(45,206,122,.15);color:var(--green);}
.chip-open{background:rgba(77,166,255,.12);color:var(--blue);}
.chip-claimed{background:rgba(155,109,255,.15);color:var(--purple);}
.chip-closed{background:rgba(107,114,128,.15);color:var(--muted);}
.chip-cat{background:rgba(240,165,0,.1);color:var(--accent);}
.item-title{font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;line-height:1.3;}
.item-desc{color:var(--muted);font-size:.88rem;line-height:1.5;}
.item-details{display:grid;grid-template-columns:1fr 1fr;gap:.5rem .8rem;margin-top:.3rem;}
.item-detail{display:flex;align-items:flex-start;gap:.4rem;font-size:.82rem;color:var(--muted);}
.item-detail i{color:var(--accent);width:14px;flex-shrink:0;margin-top:2px;}
.item-actions{display:flex;gap:.6rem;margin-top:.4rem;}
/* ── FORM STYLES ── */
.form-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:2rem;}
.form-title{font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:800;margin-bottom:.4rem;}
.form-subtitle{color:var(--muted);font-size:.9rem;margin-bottom:1.8rem;}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:1rem;}
.field{display:flex;flex-direction:column;gap:.45rem;margin-bottom:1rem;}
.field label{font-size:.82rem;font-weight:600;color:var(--muted);letter-spacing:.04em;text-transform:uppercase;}
.field input,.field select,.field textarea{
  background:var(--surface);border:1px solid var(--border);border-radius:10px;
  color:var(--text);font-family:'DM Sans',sans-serif;font-size:.9rem;padding:.7rem 1rem;
  outline:none;transition:border-color .2s,box-shadow .2s;width:100%;}
.field input:focus,.field select:focus,.field textarea:focus{
  border-color:var(--accent);box-shadow:0 0 0 3px rgba(240,165,0,.12);}
.field select option{background:var(--card);}
.field textarea{resize:vertical;min-height:90px;}
/* ── BUTTONS ── */
.btn{display:inline-flex;align-items:center;gap:.5rem;padding:.6rem 1.3rem;border-radius:9px;
  border:none;cursor:pointer;font-family:'DM Sans',sans-serif;font-size:.88rem;font-weight:600;
  text-decoration:none;transition:all .18s;white-space:nowrap;}
.btn-primary{background:var(--accent);color:#000;}
.btn-primary:hover{background:#f5b830;transform:translateY(-1px);}
.btn-secondary{background:var(--surface);color:var(--text);border:1px solid var(--border);}
.btn-secondary:hover{border-color:var(--accent);color:var(--accent);}
.btn-danger{background:rgba(224,92,58,.15);color:var(--red);border:1px solid rgba(224,92,58,.25);}
.btn-danger:hover{background:rgba(224,92,58,.25);}
.btn-success{background:rgba(45,206,122,.15);color:var(--green);border:1px solid rgba(45,206,122,.25);}
.btn-success:hover{background:rgba(45,206,122,.3);}
.btn-sm{padding:.38rem .85rem;font-size:.8rem;}
.btn-lg{padding:.85rem 2rem;font-size:1rem;border-radius:12px;}
/* ── ALERTS / FLASHES ── */
.alert{display:flex;align-items:center;gap:.75rem;padding:.9rem 1.2rem;border-radius:10px;
  margin-bottom:1.2rem;font-size:.9rem;font-weight:500;}
.alert-success{background:rgba(45,206,122,.1);border:1px solid rgba(45,206,122,.25);color:var(--green);}
.alert-danger{background:rgba(224,92,58,.1);border:1px solid rgba(224,92,58,.25);color:var(--red);}
.alert-warning{background:rgba(240,165,0,.1);border:1px solid rgba(240,165,0,.25);color:var(--accent);}
.alert-info{background:rgba(77,166,255,.1);border:1px solid rgba(77,166,255,.25);color:var(--blue);}
/* ── SECTION HEADER ── */
.section-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem;flex-wrap:wrap;gap:1rem;}
.section-title{font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:800;}
/* ── SEARCH BAR ── */
.search-bar{display:flex;gap:.75rem;align-items:center;flex-wrap:wrap;
  background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:1.2rem 1.5rem;margin-bottom:2rem;}
.search-bar .field{margin:0;flex:1;min-width:180px;}
.search-bar .field input,.search-bar .field select{padding:.55rem .9rem;font-size:.85rem;}
/* ── TABLE ── */
.tbl-wrap{overflow-x:auto;border-radius:var(--radius);border:1px solid var(--border);}
table{width:100%;border-collapse:collapse;}
thead tr{background:var(--surface);}
th{font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;
  color:var(--muted);padding:.85rem 1rem;text-align:left;border-bottom:1px solid var(--border);}
td{padding:.85rem 1rem;font-size:.87rem;border-bottom:1px solid var(--border);vertical-align:middle;}
tr:last-child td{border-bottom:none;}
tr:hover td{background:rgba(255,255,255,.015);}
/* ── TABS ── */
.tabs{display:flex;gap:.5rem;margin-bottom:1.8rem;border-bottom:1px solid var(--border);padding-bottom:0;}
.tab{padding:.65rem 1.2rem;border-radius:9px 9px 0 0;font-size:.87rem;font-weight:600;
  cursor:pointer;color:var(--muted);border:1px solid transparent;border-bottom:none;
  text-decoration:none;margin-bottom:-1px;transition:all .2s;}
.tab.active,.tab:hover{color:var(--text);background:var(--card);border-color:var(--border);}
.tab.active{color:var(--accent);border-bottom-color:var(--card);}
/* ── MODAL ── */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:200;
  align-items:center;justify-content:center;}
.modal-overlay.open{display:flex;}
.modal{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
  padding:2rem;max-width:480px;width:90%;box-shadow:var(--shadow);}
.modal-title{font-family:'Syne',sans-serif;font-weight:800;font-size:1.2rem;margin-bottom:.5rem;}
.modal-sub{color:var(--muted);font-size:.88rem;margin-bottom:1.5rem;}
/* ── DETAIL BLOCK ── */
.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;}
.detail-item label{font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:600;}
.detail-item p{font-size:.9rem;margin-top:.2rem;}
/* ── EMPTY STATE ── */
.empty{text-align:center;padding:4rem 1rem;color:var(--muted);}
.empty i{font-size:3rem;margin-bottom:1rem;opacity:.3;}
.empty p{font-size:1rem;}
/* ── LOGIN PAGE ── */
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;
  background-image:radial-gradient(ellipse 60% 40% at 50% 0%,rgba(240,165,0,.07),transparent);}
.login-box{background:var(--card);border:1px solid var(--border);border-radius:20px;
  padding:2.5rem;width:100%;max-width:420px;box-shadow:var(--shadow);}
.login-logo{display:flex;align-items:center;gap:.6rem;margin-bottom:2rem;
  font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:800;}
.login-logo span{color:var(--accent);}
.divider{display:flex;align-items:center;gap:.8rem;color:var(--muted);font-size:.8rem;margin:1rem 0;}
.divider::before,.divider::after{content:'';flex:1;height:1px;background:var(--border);}
/* ── ADMIN PANEL ── */
.admin-aside{position:fixed;top:64px;left:0;bottom:0;width:220px;background:var(--surface);
  border-right:1px solid var(--border);padding:1.5rem 1rem;display:flex;flex-direction:column;gap:.25rem;}
.admin-aside a{display:flex;align-items:center;gap:.7rem;padding:.6rem .9rem;border-radius:9px;
  color:var(--muted);text-decoration:none;font-size:.875rem;font-weight:500;transition:all .18s;}
.admin-aside a:hover,.admin-aside a.active{color:var(--text);background:var(--border);}
.admin-aside a.active{color:var(--accent);}
.admin-aside .aside-label{font-size:.7rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.08em;color:var(--muted);padding:.5rem .9rem;margin-top:.5rem;}
.admin-main{margin-left:220px;padding:2rem;}
/* ── RESPONSIVE ── */
@media(max-width:768px){
  .form-row{grid-template-columns:1fr;}
  .stats-bar{grid-template-columns:repeat(2,1fr);}
  .detail-grid{grid-template-columns:1fr;}
  .admin-aside{display:none;}
  .admin-main{margin-left:0;}
  nav{padding:0 1rem;}
}
/* ── ANIMATIONS ── */
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
.fade-up{animation:fadeUp .4s ease both;}
.fade-up-1{animation-delay:.05s}
.fade-up-2{animation-delay:.1s}
.fade-up-3{animation-delay:.15s}
.fade-up-4{animation-delay:.2s}
/* scrollbar */
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:99px}
</style>
</head>
<body>
{% if session.get('user_id') %}
<nav>
  <a class="nav-brand" href="/dashboard"><i class="fa-solid fa-satellite-dish" style="color:var(--accent)"></i>Campus<span>Trace</span></a>
  <div class="nav-links">
    <a href="/dashboard" {% if request.path=='/dashboard' %}class="active"{% endif %}>Dashboard</a>
    <a href="/report/lost" {% if request.path=='/report/lost' %}class="active"{% endif %} style="color:#f08060"><i class="fa-solid fa-triangle-exclamation"></i> Lost</a>
    <a href="/report/found" {% if request.path=='/report/found' %}class="active"{% endif %} style="color:var(--green)"><i class="fa-solid fa-hand-holding-heart"></i> Found</a>
    <a href="/search" {% if request.path=='/search' %}class="active"{% endif %}><i class="fa-solid fa-magnifying-glass"></i> Search</a>
    {% if session.get('role')=='admin' %}
    <a href="/admin" {% if '/admin' in request.path %}class="active"{% endif %}><i class="fa-solid fa-shield"></i> Admin</a>
    {% endif %}
    <a href="/profile" {% if request.path=='/profile' %}class="active"{% endif %}><i class="fa-solid fa-user-circle"></i> {{session.get('name','Me')|truncate(10)}}</a>
    <a href="/logout" class="btn-accent">Sign Out</a>
  </div>
</nav>
{% endif %}

{% with messages = get_flashed_messages(with_categories=true) %}
{% if messages %}
<div style="max-width:1200px;margin:.8rem auto;padding:0 1.5rem;">
{% for category,message in messages %}
<div class="alert alert-{{category}}">
  <i class="fa-solid {% if category=='success' %}fa-circle-check{% elif category=='danger' %}fa-circle-xmark{% else %}fa-circle-info{% endif %}"></i>
  {{message}}
</div>
{% endfor %}
</div>
{% endif %}
{% endwith %}

{% block content %}{% endblock %}

<script>
function openModal(id){document.getElementById(id).classList.add('open');}
function closeModal(id){document.getElementById(id).classList.remove('open');}
document.querySelectorAll('.modal-overlay').forEach(m=>{
  m.addEventListener('click',e=>{if(e.target===m)m.classList.remove('open');});
});
</script>
</body></html>"""

# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# ── LOGIN ──
LOGIN_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """{% block content %}
<div class="login-wrap">
  <div class="login-box fade-up">
    <div class="login-logo"><i class="fa-solid fa-satellite-dish" style="color:var(--accent);font-size:1.5rem"></i>Campus<span>Trace</span></div>
    <h2 style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;margin-bottom:.3rem">Welcome back</h2>
    <p style="color:var(--muted);font-size:.88rem;margin-bottom:1.8rem">Sign in to access the Lost & Found portal</p>
    <form method="POST" action="/login">
      <div class="field">
        <label><i class="fa-solid fa-user"></i> Username</label>
        <input name="username" placeholder="Enter username" required autofocus>
      </div>
      <div class="field">
        <label><i class="fa-solid fa-lock"></i> Password</label>
        <input type="password" name="password" placeholder="Enter password" required>
      </div>
      <button class="btn btn-primary btn-lg" style="width:100%;justify-content:center;margin-top:.5rem">
        <i class="fa-solid fa-arrow-right-to-bracket"></i> Sign In
      </button>
    </form>
    <div class="divider">or</div>
    <a href="/register" class="btn btn-secondary" style="width:100%;justify-content:center">
      <i class="fa-solid fa-user-plus"></i> Create Account
    </a>
    <p style="text-align:center;color:var(--muted);font-size:.78rem;margin-top:1.5rem">
      <i class="fa-solid fa-shield-halved"></i> Demo — Admin: <b>admin/admin123</b> &nbsp;|&nbsp; Student: <b>student1/pass123</b>
    </p>
  </div>
</div>
{% endblock %}""")

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        un = request.form.get('username','').strip()
        pw = request.form.get('password','')
        conn = get_db()
        u = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (un, hash_pw(pw))).fetchone()
        conn.close()
        if u:
            session['user_id'] = u['id']
            session['username'] = u['username']
            session['name'] = u['full_name']
            session['role'] = u['role']
            flash(f"Welcome back, {u['full_name']}!", 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials. Please try again.', 'danger')
    return render_template_string(LOGIN_HTML)

# ── REGISTER ──
REGISTER_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """{% block content %}
<div class="login-wrap">
  <div class="login-box fade-up" style="max-width:480px">
    <div class="login-logo"><i class="fa-solid fa-satellite-dish" style="color:var(--accent);font-size:1.5rem"></i>Campus<span>Trace</span></div>
    <h2 style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;margin-bottom:.3rem">Create Account</h2>
    <p style="color:var(--muted);font-size:.88rem;margin-bottom:1.8rem">Join the campus Lost & Found network</p>
    <form method="POST" action="/register">
      <div class="form-row">
        <div class="field">
          <label>Full Name</label>
          <input name="full_name" placeholder="Your name" required>
        </div>
        <div class="field">
          <label>Username</label>
          <input name="username" placeholder="Choose username" required>
        </div>
      </div>
      <div class="field">
        <label>Email</label>
        <input type="email" name="email" placeholder="your@college.edu">
      </div>
      <div class="form-row">
        <div class="field">
          <label>Password</label>
          <input type="password" name="password" placeholder="Min 6 chars" required>
        </div>
        <div class="field">
          <label>Confirm Password</label>
          <input type="password" name="confirm" placeholder="Repeat password" required>
        </div>
      </div>
      <button class="btn btn-primary btn-lg" style="width:100%;justify-content:center;margin-top:.3rem">
        <i class="fa-solid fa-user-plus"></i> Register
      </button>
    </form>
    <p style="text-align:center;margin-top:1.2rem;font-size:.88rem;color:var(--muted)">
      Already have an account? <a href="/login" style="color:var(--accent)">Sign in</a>
    </p>
  </div>
</div>
{% endblock %}""")

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        fn = request.form.get('full_name','').strip()
        un = request.form.get('username','').strip()
        em = request.form.get('email','').strip()
        pw = request.form.get('password','')
        cf = request.form.get('confirm','')
        if pw != cf:
            flash('Passwords do not match.', 'danger')
            return render_template_string(REGISTER_HTML)
        if len(pw) < 6:
            flash('Password must be at least 6 characters.', 'warning')
            return render_template_string(REGISTER_HTML)
        try:
            conn = get_db()
            conn.execute("INSERT INTO users(username,password,full_name,email) VALUES(?,?,?,?)",
                         (un, hash_pw(pw), fn, em))
            conn.commit()
            conn.close()
            flash('Account created! Please login.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Username already taken. Try another.', 'danger')
    return render_template_string(REGISTER_HTML)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been signed out.', 'info')
    return redirect(url_for('login'))

# ── DASHBOARD ──
DASHBOARD_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """{% block content %}
<div class="page">
  <div class="hero fade-up">
    <div class="hero-eyebrow"><i class="fa-solid fa-wifi"></i> Live Portal</div>
    <h1>Find What's <em>Lost</em>,<br>Return What's <em>Found</em></h1>
    <p>A centralized digital platform for tracking lost and found electronic devices across campus. Fast, transparent, and efficient.</p>
    <div class="hero-actions">
      <a href="/report/lost" class="btn btn-lg" style="background:linear-gradient(135deg,#e05c3a,#f08060);color:#fff;"><i class="fa-solid fa-triangle-exclamation"></i> Report Lost</a>
      <a href="/report/found" class="btn btn-lg" style="background:linear-gradient(135deg,#1a9e5c,#2dce7a);color:#fff;"><i class="fa-solid fa-hand-holding-heart"></i> Report Found</a>
      <a href="/search" class="btn btn-secondary btn-lg"><i class="fa-solid fa-magnifying-glass"></i> Search Items</a>
    </div>
  </div>

  <div class="stats-bar fade-up fade-up-1">
    <div class="stat-cell"><div class="stat-num">{{stats.total}}</div><div class="stat-lbl">Total Reports</div></div>
    <div class="stat-cell"><div class="stat-num" style="color:#f08060">{{stats.lost}}</div><div class="stat-lbl">Lost Items</div></div>
    <div class="stat-cell"><div class="stat-num" style="color:var(--green)">{{stats.found}}</div><div class="stat-lbl">Found Items</div></div>
    <div class="stat-cell"><div class="stat-num" style="color:var(--purple)">{{stats.claimed}}</div><div class="stat-lbl">Claimed/Returned</div></div>
  </div>

  <div class="section-header fade-up fade-up-2">
    <div class="section-title">Recent Reports</div>
    <a href="/search" class="btn btn-secondary btn-sm"><i class="fa-solid fa-arrow-right"></i> View All</a>
  </div>

  {% if items %}
  <div class="card-grid cols-2 fade-up fade-up-3">
  {% for item in items %}
    <div class="card item-card">
      <div class="item-meta">
        <span class="chip {{'chip-lost' if item.type=='lost' else 'chip-found'}}">
          <i class="fa-solid {{'fa-triangle-exclamation' if item.type=='lost' else 'fa-hand-holding-heart'}}"></i>
          {{item.type|upper}}
        </span>
        <span class="chip chip-cat"><i class="fa-solid fa-tag"></i> {{item.category}}</span>
        <span class="chip {{'chip-open' if item.status=='open' else ('chip-claimed' if item.status=='claimed' else 'chip-closed')}}">{{item.status}}</span>
      </div>
      <div class="item-title">{{item.item_name}}</div>
      <div class="item-desc">{{item.description or 'No description provided.'}}</div>
      <div class="item-details">
        <div class="item-detail"><i class="fa-solid fa-location-dot"></i><span>{{item.location}}</span></div>
        <div class="item-detail"><i class="fa-solid fa-calendar"></i><span>{{item.date_lost_found or item.date_reported}}</span></div>
        {% if item.brand %}<div class="item-detail"><i class="fa-solid fa-copyright"></i><span>{{item.brand}}</span></div>{% endif %}
        {% if item.color %}<div class="item-detail"><i class="fa-solid fa-palette"></i><span>{{item.color}}</span></div>{% endif %}
      </div>
      <div class="item-actions">
        <a href="/item/{{item.id}}" class="btn btn-secondary btn-sm"><i class="fa-solid fa-eye"></i> Details</a>
        {% if item.status=='open' and session.get('user_id') != item.user_id %}
        <a href="/claim/{{item.id}}" class="btn btn-success btn-sm"><i class="fa-solid fa-hand"></i> Claim</a>
        {% endif %}
      </div>
    </div>
  {% endfor %}
  </div>
  {% else %}
  <div class="empty"><i class="fa-solid fa-box-open"></i><p>No items reported yet.</p></div>
  {% endif %}
</div>
{% endblock %}""")

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    stats = {
        'total': conn.execute("SELECT COUNT(*) FROM items").fetchone()[0],
        'lost':  conn.execute("SELECT COUNT(*) FROM items WHERE type='lost'").fetchone()[0],
        'found': conn.execute("SELECT COUNT(*) FROM items WHERE type='found'").fetchone()[0],
        'claimed':conn.execute("SELECT COUNT(*) FROM items WHERE status IN ('claimed','closed')").fetchone()[0],
    }
    items = conn.execute("SELECT * FROM items ORDER BY created DESC LIMIT 8").fetchall()
    conn.close()
    return render_template_string(DASHBOARD_HTML, stats=stats, items=items)

# ── REPORT SELECTION PAGE ──
REPORT_SELECT_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """{% block content %}
<style>
.report-choice-card{
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1.2rem;
  padding:3rem 2rem;border-radius:20px;border:2px solid var(--border);
  background:var(--card);text-decoration:none;transition:all .25s;cursor:pointer;
  position:relative;overflow:hidden;
}
.report-choice-card::before{
  content:'';position:absolute;inset:0;opacity:0;transition:opacity .3s;
}
.report-choice-card.lost-card::before{background:radial-gradient(ellipse at 50% 0%,rgba(224,92,58,.12),transparent 70%);}
.report-choice-card.found-card::before{background:radial-gradient(ellipse at 50% 0%,rgba(45,206,122,.12),transparent 70%);}
.report-choice-card:hover::before{opacity:1;}
.report-choice-card.lost-card:hover{border-color:#f08060;transform:translateY(-4px);box-shadow:0 20px 48px rgba(224,92,58,.15);}
.report-choice-card.found-card:hover{border-color:var(--green);transform:translateY(-4px);box-shadow:0 20px 48px rgba(45,206,122,.15);}
.choice-icon{width:90px;height:90px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:2.2rem;position:relative;z-index:1;}
.choice-title{font-family:'Syne',sans-serif;font-weight:800;font-size:1.5rem;position:relative;z-index:1;}
.choice-desc{color:var(--muted);font-size:.9rem;text-align:center;line-height:1.6;max-width:240px;position:relative;z-index:1;}
.choice-arrow{font-size:1.2rem;position:relative;z-index:1;opacity:.5;transition:opacity .2s,transform .2s;}
.report-choice-card:hover .choice-arrow{opacity:1;transform:translateX(4px);}
.choice-tips{display:flex;flex-direction:column;gap:.5rem;margin-top:.5rem;width:100%;position:relative;z-index:1;}
.choice-tip{display:flex;align-items:center;gap:.6rem;font-size:.8rem;color:var(--muted);}
</style>

<div class="page" style="max-width:900px">
  <div style="text-align:center;margin-bottom:3rem;" class="fade-up">
    <div class="hero-eyebrow" style="margin:0 auto 1.2rem"><i class="fa-solid fa-file-pen"></i> Report Center</div>
    <h2 style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;letter-spacing:-.02em;margin-bottom:.6rem">What would you like to report?</h2>
    <p style="color:var(--muted);font-size:.95rem">Select the type of report to open its dedicated form</p>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;margin-bottom:3rem;" class="fade-up fade-up-1">

    <!-- LOST CARD -->
    <a href="/report/lost" class="report-choice-card lost-card">
      <div class="choice-icon" style="background:rgba(224,92,58,.15);color:#f08060;">
        <i class="fa-solid fa-triangle-exclamation"></i>
      </div>
      <div class="choice-title" style="color:#f08060;">Lost Report</div>
      <div class="choice-desc">I lost an electronic item on campus and need help locating or recovering it.</div>
      <div class="choice-tips">
        <div class="choice-tip"><i class="fa-solid fa-circle-dot" style="color:#f08060;font-size:.6rem"></i> Describe your item in detail</div>
        <div class="choice-tip"><i class="fa-solid fa-circle-dot" style="color:#f08060;font-size:.6rem"></i> Mention where you last had it</div>
        <div class="choice-tip"><i class="fa-solid fa-circle-dot" style="color:#f08060;font-size:.6rem"></i> Provide contact info for updates</div>
      </div>
      <div class="choice-arrow" style="color:#f08060;"><i class="fa-solid fa-arrow-right"></i> Go to Lost Form</div>
    </a>

    <!-- FOUND CARD -->
    <a href="/report/found" class="report-choice-card found-card">
      <div class="choice-icon" style="background:rgba(45,206,122,.15);color:var(--green);">
        <i class="fa-solid fa-hand-holding-heart"></i>
      </div>
      <div class="choice-title" style="color:var(--green);">Found Report</div>
      <div class="choice-desc">I found someone's electronic item and want to help them get it back safely.</div>
      <div class="choice-tips">
        <div class="choice-tip"><i class="fa-solid fa-circle-dot" style="color:var(--green);font-size:.6rem"></i> Describe the item you found</div>
        <div class="choice-tip"><i class="fa-solid fa-circle-dot" style="color:var(--green);font-size:.6rem"></i> Mention where you found it</div>
        <div class="choice-tip"><i class="fa-solid fa-circle-dot" style="color:var(--green);font-size:.6rem"></i> Item stays with you or security</div>
      </div>
      <div class="choice-arrow" style="color:var(--green);"><i class="fa-solid fa-arrow-right"></i> Go to Found Form</div>
    </a>

  </div>

  <div style="background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.4rem 1.8rem;
    display:flex;align-items:center;gap:1rem;" class="fade-up fade-up-2">
    <i class="fa-solid fa-lightbulb" style="color:var(--accent);font-size:1.3rem;flex-shrink:0"></i>
    <p style="font-size:.87rem;color:var(--muted);line-height:1.6">
      <strong style="color:var(--text)">Tip:</strong> The more details you provide, the better your chances of recovery.
      Include brand, color, model, and any unique identifiers like stickers or scratches.
    </p>
  </div>
</div>
{% endblock %}""")

# ── LOST REPORT PAGE ──
LOST_REPORT_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """{% block content %}
<style>
:root{ --form-accent:#e05c3a; --form-accent-soft:rgba(224,92,58,.12); --form-accent-border:rgba(224,92,58,.3); }
body{background-image:radial-gradient(ellipse 70% 40% at 50% -10%,rgba(224,92,58,.06),transparent);}
.lost-header{background:linear-gradient(135deg,rgba(224,92,58,.1),rgba(224,92,58,.03));
  border:1px solid rgba(224,92,58,.2);border-radius:16px;padding:1.8rem 2rem;
  display:flex;align-items:center;gap:1.2rem;margin-bottom:2rem;}
.lost-header-icon{width:60px;height:60px;border-radius:14px;background:rgba(224,92,58,.15);
  display:flex;align-items:center;justify-content:center;color:#f08060;font-size:1.6rem;flex-shrink:0;}
.step-bar{display:flex;gap:.5rem;margin-bottom:2rem;}
.step{flex:1;height:4px;border-radius:99px;background:var(--border);transition:background .3s;}
.step.done{background:#f08060;}
.section-divider{border:none;border-top:1px solid var(--border);margin:1.4rem 0;}
.section-label{font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;
  color:#f08060;margin-bottom:1rem;display:flex;align-items:center;gap:.5rem;}
.field input:focus,.field select:focus,.field textarea:focus{
  border-color:#f08060 !important;box-shadow:0 0 0 3px rgba(224,92,58,.12) !important;}
</style>

<div class="page" style="max-width:820px">
  <div class="section-header fade-up">
    <a href="/report" class="btn btn-secondary btn-sm"><i class="fa-solid fa-arrow-left"></i> Back</a>
    <div style="display:flex;align-items:center;gap:.6rem">
      <span class="chip chip-lost"><i class="fa-solid fa-triangle-exclamation"></i> LOST REPORT</span>
    </div>
  </div>

  <div class="lost-header fade-up fade-up-1">
    <div class="lost-header-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
    <div>
      <div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;margin-bottom:.3rem;color:#f08060;">
        Lost Item Report
      </div>
      <div style="color:var(--muted);font-size:.9rem;line-height:1.5;">
        Fill in as many details as possible. Our system will match your report against found items and notify you instantly.
      </div>
    </div>
  </div>

  <div class="form-card fade-up fade-up-2">
    <form method="POST" action="/report/lost">
      <input type="hidden" name="type" value="lost">

      <div class="section-label"><i class="fa-solid fa-tag"></i> Item Information</div>
      <div class="form-row">
        <div class="field">
          <label>Category *</label>
          <select name="category" required>
            <option value="">— Select Category —</option>
            <option>Mobile Phone</option>
            <option>Earphones / AirPods</option>
            <option>Charger / Adapter</option>
            <option>Smart Watch</option>
            <option>USB Drive</option>
            <option>Calculator</option>
            <option>Laptop</option>
            <option>Tablet / iPad</option>
            <option>Camera</option>
            <option>Other Electronic</option>
          </select>
        </div>
        <div class="field">
          <label>Item Name *</label>
          <input name="item_name" placeholder="e.g. Samsung Galaxy S22" required>
        </div>
      </div>
      <div class="form-row">
        <div class="field">
          <label>Brand / Manufacturer</label>
          <input name="brand" placeholder="e.g. Apple, Samsung, Sony, Noise">
        </div>
        <div class="field">
          <label>Primary Color</label>
          <input name="color" placeholder="e.g. Midnight Black, Rose Gold">
        </div>
      </div>
      <div class="field">
        <label>Identifying Description *</label>
        <textarea name="description" rows="3" placeholder="Describe unique features — stickers, cracks, case type, model number on back, engraving, wallpaper visible, any scratches or dents…" required></textarea>
      </div>

      <hr class="section-divider">
      <div class="section-label"><i class="fa-solid fa-location-dot"></i> Where & When Lost</div>
      <div class="form-row">
        <div class="field">
          <label>Last Seen Location *</label>
          <input name="location" placeholder="e.g. Library 2nd Floor, Cafeteria Table 5, Block-A Room 101" required>
        </div>
        <div class="field">
          <label>Date Lost *</label>
          <input type="date" name="date_lost_found" required>
        </div>
      </div>
      <div class="field">
        <label>Additional Location Notes</label>
        <input name="location_notes" placeholder="e.g. Near the window seat, left it on the charging table…">
      </div>

      <hr class="section-divider">
      <div class="section-label"><i class="fa-solid fa-address-card"></i> Your Contact Details</div>
      <div class="form-row">
        <div class="field">
          <label>Your Full Name *</label>
          <input name="contact_name" value="{{session.get('name','')}}" required>
        </div>
        <div class="field">
          <label>College Email</label>
          <input type="email" name="contact_email" placeholder="yourname@college.edu">
        </div>
      </div>
      <div class="field" style="max-width:300px">
        <label>Mobile Number</label>
        <input name="contact_phone" placeholder="10-digit number" maxlength="10">
      </div>

      <div style="display:flex;gap:1rem;align-items:center;margin-top:1.5rem;flex-wrap:wrap">
        <button type="submit" class="btn btn-lg" style="background:linear-gradient(135deg,#c94a2b,#f08060);color:#fff;gap:.6rem;">
          <i class="fa-solid fa-paper-plane"></i> Submit Lost Report
        </button>
        <a href="/report" class="btn btn-secondary">Cancel</a>
        <span style="color:var(--muted);font-size:.8rem;margin-left:auto"><i class="fa-solid fa-shield"></i> Your info is kept private</span>
      </div>
    </form>
  </div>
</div>
{% endblock %}""")

# ── FOUND REPORT PAGE ──
FOUND_REPORT_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """{% block content %}
<style>
:root{ --form-accent:#2dce7a; --form-accent-soft:rgba(45,206,122,.12); --form-accent-border:rgba(45,206,122,.3); }
body{background-image:radial-gradient(ellipse 70% 40% at 50% -10%,rgba(45,206,122,.05),transparent);}
.found-header{background:linear-gradient(135deg,rgba(45,206,122,.1),rgba(45,206,122,.02));
  border:1px solid rgba(45,206,122,.2);border-radius:16px;padding:1.8rem 2rem;
  display:flex;align-items:center;gap:1.2rem;margin-bottom:2rem;}
.found-header-icon{width:60px;height:60px;border-radius:14px;background:rgba(45,206,122,.15);
  display:flex;align-items:center;justify-content:center;color:var(--green);font-size:1.6rem;flex-shrink:0;}
.section-divider{border:none;border-top:1px solid var(--border);margin:1.4rem 0;}
.section-label{font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;
  color:var(--green);margin-bottom:1rem;display:flex;align-items:center;gap:.5rem;}
.field input:focus,.field select:focus,.field textarea:focus{
  border-color:var(--green) !important;box-shadow:0 0 0 3px rgba(45,206,122,.12) !important;}
</style>

<div class="page" style="max-width:820px">
  <div class="section-header fade-up">
    <a href="/report" class="btn btn-secondary btn-sm"><i class="fa-solid fa-arrow-left"></i> Back</a>
    <div style="display:flex;align-items:center;gap:.6rem">
      <span class="chip chip-found"><i class="fa-solid fa-hand-holding-heart"></i> FOUND REPORT</span>
    </div>
  </div>

  <div class="found-header fade-up fade-up-1">
    <div class="found-header-icon"><i class="fa-solid fa-hand-holding-heart"></i></div>
    <div>
      <div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;margin-bottom:.3rem;color:var(--green);">
        Found Item Report
      </div>
      <div style="color:var(--muted);font-size:.9rem;line-height:1.5;">
        Thank you for taking the initiative! Fill in the details below and the rightful owner will be notified to contact you or the security office.
      </div>
    </div>
  </div>

  <div class="form-card fade-up fade-up-2">
    <form method="POST" action="/report/found">
      <input type="hidden" name="type" value="found">

      <div class="section-label"><i class="fa-solid fa-box"></i> Item Details</div>
      <div class="form-row">
        <div class="field">
          <label>Category *</label>
          <select name="category" required>
            <option value="">— Select Category —</option>
            <option>Mobile Phone</option>
            <option>Earphones / AirPods</option>
            <option>Charger / Adapter</option>
            <option>Smart Watch</option>
            <option>USB Drive</option>
            <option>Calculator</option>
            <option>Laptop</option>
            <option>Tablet / iPad</option>
            <option>Camera</option>
            <option>Other Electronic</option>
          </select>
        </div>
        <div class="field">
          <label>Item Name *</label>
          <input name="item_name" placeholder="e.g. JBL Wireless Earbuds, Blue USB Drive" required>
        </div>
      </div>
      <div class="form-row">
        <div class="field">
          <label>Brand (if visible)</label>
          <input name="brand" placeholder="e.g. Apple, JBL, Noise, Casio">
        </div>
        <div class="field">
          <label>Color</label>
          <input name="color" placeholder="e.g. White, Black, Orange">
        </div>
      </div>
      <div class="field">
        <label>Item Description *</label>
        <textarea name="description" rows="3" placeholder="Describe the item's condition, any visible markings, model written on it, case, accessories found along with it…" required></textarea>
      </div>

      <hr class="section-divider">
      <div class="section-label"><i class="fa-solid fa-map-pin"></i> Where & When Found</div>
      <div class="form-row">
        <div class="field">
          <label>Location Found *</label>
          <input name="location" placeholder="e.g. Cafeteria Table 3, Block-B Bench, Main Gate, Library" required>
        </div>
        <div class="field">
          <label>Date Found *</label>
          <input type="date" name="date_lost_found" required>
        </div>
      </div>

      <hr class="section-divider">
      <div class="section-label"><i class="fa-solid fa-warehouse"></i> Item Custody</div>
      <div class="field">
        <label>Where is the item currently kept? *</label>
        <select name="custody_location" required>
          <option value="">— Select —</option>
          <option value="With me (reporter)">With me (I'll handover when claimed)</option>
          <option value="Security Office">Submitted to Security Office</option>
          <option value="Department Office">Submitted to Department Office</option>
          <option value="Library Counter">Submitted to Library Counter</option>
          <option value="Other">Other (mentioned in description)</option>
        </select>
      </div>

      <hr class="section-divider">
      <div class="section-label"><i class="fa-solid fa-address-card"></i> Your Contact Details</div>
      <div class="form-row">
        <div class="field">
          <label>Your Full Name *</label>
          <input name="contact_name" value="{{session.get('name','')}}" required>
        </div>
        <div class="field">
          <label>College Email</label>
          <input type="email" name="contact_email" placeholder="yourname@college.edu">
        </div>
      </div>
      <div class="field" style="max-width:300px">
        <label>Mobile Number</label>
        <input name="contact_phone" placeholder="10-digit number" maxlength="10">
      </div>

      <div style="display:flex;gap:1rem;align-items:center;margin-top:1.5rem;flex-wrap:wrap">
        <button type="submit" class="btn btn-lg" style="background:linear-gradient(135deg,#1a9e5c,#2dce7a);color:#fff;gap:.6rem;">
          <i class="fa-solid fa-paper-plane"></i> Submit Found Report
        </button>
        <a href="/report" class="btn btn-secondary">Cancel</a>
        <span style="color:var(--muted);font-size:.8rem;margin-left:auto"><i class="fa-solid fa-heart" style="color:var(--green)"></i> Thank you for helping!</span>
      </div>
    </form>
  </div>
</div>
{% endblock %}""")

@app.route('/report')
@login_required
def report():
    return render_template_string(REPORT_SELECT_HTML)

@app.route('/report/lost', methods=['GET','POST'])
@login_required
def report_lost():
    if request.method == 'POST':
        f = request.form
        # Append custody info to description for found items
        desc = f.get('description','')
        loc_notes = f.get('location_notes','')
        if loc_notes:
            desc = desc + (f"\nLocation notes: {loc_notes}" if desc else f"Location notes: {loc_notes}")
        conn = get_db()
        conn.execute("""INSERT INTO items(type,category,item_name,description,brand,color,location,
                     date_reported,date_lost_found,contact_name,contact_email,contact_phone,user_id)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     ('lost', f['category'], f['item_name'], desc,
                      f.get('brand',''), f.get('color',''), f['location'],
                      datetime.today().strftime('%Y-%m-%d'), f.get('date_lost_found',''),
                      f['contact_name'], f.get('contact_email',''), f.get('contact_phone',''),
                      session['user_id']))
        conn.commit()
        conn.close()
        flash('Lost item reported! We will notify you if a matching found item is reported.', 'success')
        return redirect(url_for('dashboard'))
    return render_template_string(LOST_REPORT_HTML)

@app.route('/report/found', methods=['GET','POST'])
@login_required
def report_found():
    if request.method == 'POST':
        f = request.form
        desc = f.get('description','')
        custody = f.get('custody_location','')
        if custody:
            desc = desc + (f"\nItem currently at: {custody}" if desc else f"Item currently at: {custody}")
        conn = get_db()
        conn.execute("""INSERT INTO items(type,category,item_name,description,brand,color,location,
                     date_reported,date_lost_found,contact_name,contact_email,contact_phone,user_id)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     ('found', f['category'], f['item_name'], desc,
                      f.get('brand',''), f.get('color',''), f['location'],
                      datetime.today().strftime('%Y-%m-%d'), f.get('date_lost_found',''),
                      f['contact_name'], f.get('contact_email',''), f.get('contact_phone',''),
                      session['user_id']))
        conn.commit()
        conn.close()
        flash('Found item reported! Thank you for helping someone recover their belongings.', 'success')
        return redirect(url_for('dashboard'))
    return render_template_string(FOUND_REPORT_HTML)

# ── SEARCH ──
SEARCH_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """{% block content %}
<div class="page">
  <div class="section-header fade-up">
    <div class="section-title"><i class="fa-solid fa-magnifying-glass" style="color:var(--accent)"></i> Search Items</div>
  </div>

  <div class="search-bar fade-up fade-up-1">
    <form method="GET" action="/search" style="display:contents">
      <div class="field" style="flex:2">
        <label>Keyword</label>
        <input name="q" value="{{q}}" placeholder="Search by name, brand, description…">
      </div>
      <div class="field">
        <label>Type</label>
        <select name="type">
          <option value="">All Types</option>
          <option value="lost" {{'selected' if type=='lost'}}>Lost</option>
          <option value="found" {{'selected' if type=='found'}}>Found</option>
        </select>
      </div>
      <div class="field">
        <label>Category</label>
        <select name="category">
          <option value="">All Categories</option>
          <option>Mobile Phone</option>
          <option>Earphones / AirPods</option>
          <option>Charger / Adapter</option>
          <option>Smart Watch</option>
          <option>USB Drive</option>
          <option>Calculator</option>
          <option>Laptop</option>
          <option>Tablet / iPad</option>
          <option>Camera</option>
          <option>Other Electronic</option>
        </select>
      </div>
      <div class="field">
        <label>Status</label>
        <select name="status">
          <option value="">All Statuses</option>
          <option value="open" {{'selected' if status=='open'}}>Open</option>
          <option value="claimed" {{'selected' if status=='claimed'}}>Claimed</option>
          <option value="closed" {{'selected' if status=='closed'}}>Closed</option>
        </select>
      </div>
      <button type="submit" class="btn btn-primary" style="margin-top:auto"><i class="fa-solid fa-search"></i> Search</button>
      <a href="/search" class="btn btn-secondary" style="margin-top:auto"><i class="fa-solid fa-xmark"></i></a>
    </form>
  </div>

  <div style="color:var(--muted);font-size:.85rem;margin-bottom:1.2rem">
    Showing <strong style="color:var(--text)">{{items|length}}</strong> result(s)
  </div>

  {% if items %}
  <div class="card-grid cols-2 fade-up fade-up-2">
  {% for item in items %}
    <div class="card item-card">
      <div class="item-meta">
        <span class="chip {{'chip-lost' if item.type=='lost' else 'chip-found'}}">
          <i class="fa-solid {{'fa-triangle-exclamation' if item.type=='lost' else 'fa-hand-holding-heart'}}"></i>
          {{item.type|upper}}
        </span>
        <span class="chip chip-cat">{{item.category}}</span>
        <span class="chip {{'chip-open' if item.status=='open' else ('chip-claimed' if item.status=='claimed' else 'chip-closed')}}">{{item.status}}</span>
      </div>
      <div class="item-title">{{item.item_name}}</div>
      <div class="item-desc">{{item.description or 'No description.'}}</div>
      <div class="item-details">
        <div class="item-detail"><i class="fa-solid fa-location-dot"></i><span>{{item.location}}</span></div>
        <div class="item-detail"><i class="fa-solid fa-calendar"></i><span>{{item.date_lost_found or item.date_reported}}</span></div>
        {% if item.brand %}<div class="item-detail"><i class="fa-solid fa-copyright"></i><span>{{item.brand}}</span></div>{% endif %}
        {% if item.color %}<div class="item-detail"><i class="fa-solid fa-palette"></i><span>{{item.color}}</span></div>{% endif %}
      </div>
      <div class="item-actions">
        <a href="/item/{{item.id}}" class="btn btn-secondary btn-sm"><i class="fa-solid fa-eye"></i> Details</a>
        {% if item.status=='open' %}
        <a href="/claim/{{item.id}}" class="btn btn-success btn-sm"><i class="fa-solid fa-hand"></i> Claim / Contact</a>
        {% endif %}
      </div>
    </div>
  {% endfor %}
  </div>
  {% else %}
  <div class="empty fade-up">
    <i class="fa-solid fa-binoculars"></i>
    <p>No items match your search. Try different keywords.</p>
  </div>
  {% endif %}
</div>
{% endblock %}""")

@app.route('/search')
@login_required
def search():
    q = request.args.get('q','').strip()
    typ = request.args.get('type','')
    cat = request.args.get('category','')
    status = request.args.get('status','')
    conn = get_db()
    sql = "SELECT * FROM items WHERE 1=1"
    params = []
    if q:
        sql += " AND (item_name LIKE ? OR description LIKE ? OR brand LIKE ? OR location LIKE ?)"
        params += [f'%{q}%']*4
    if typ:
        sql += " AND type=?"; params.append(typ)
    if cat:
        sql += " AND category=?"; params.append(cat)
    if status:
        sql += " AND status=?"; params.append(status)
    sql += " ORDER BY created DESC"
    items = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template_string(SEARCH_HTML, items=items, q=q, type=typ, category=cat, status=status)

# ── ITEM DETAIL ──
DETAIL_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """{% block content %}
<div class="page" style="max-width:820px">
  <div class="section-header fade-up">
    <a href="/search" class="btn btn-secondary btn-sm"><i class="fa-solid fa-arrow-left"></i> Back</a>
    <div class="item-meta">
      <span class="chip {{'chip-lost' if item.type=='lost' else 'chip-found'}}">{{item.type|upper}}</span>
      <span class="chip {{'chip-open' if item.status=='open' else ('chip-claimed' if item.status=='claimed' else 'chip-closed')}}">{{item.status|upper}}</span>
    </div>
  </div>

  <div class="form-card fade-up fade-up-1">
    <h2 style="font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:800;margin-bottom:.3rem">{{item.item_name}}</h2>
    <p style="color:var(--muted);margin-bottom:1.8rem">{{item.category}} &bull; Reported on {{item.date_reported}}</p>

    <div class="detail-grid" style="margin-bottom:1.8rem">
      <div class="detail-item"><label>Brand</label><p>{{item.brand or '—'}}</p></div>
      <div class="detail-item"><label>Color</label><p>{{item.color or '—'}}</p></div>
      <div class="detail-item"><label>Location</label><p>{{item.location}}</p></div>
      <div class="detail-item"><label>Date Lost/Found</label><p>{{item.date_lost_found or '—'}}</p></div>
      <div class="detail-item" style="grid-column:1/-1"><label>Description</label><p>{{item.description or 'No additional description.'}}</p></div>
    </div>

    <div style="border-top:1px solid var(--border);padding-top:1.2rem;margin-bottom:1.5rem">
      <p style="font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin-bottom:1rem">Contact Person</p>
      <div class="detail-grid">
        <div class="detail-item"><label>Name</label><p>{{item.contact_name}}</p></div>
        <div class="detail-item"><label>Email</label><p>{{item.contact_email or '—'}}</p></div>
        <div class="detail-item"><label>Phone</label><p>{{item.contact_phone or '—'}}</p></div>
      </div>
    </div>

    <div class="item-actions">
      {% if item.status=='open' and session.get('user_id') != item.user_id %}
      <a href="/claim/{{item.id}}" class="btn btn-success"><i class="fa-solid fa-hand"></i> Claim This Item</a>
      {% endif %}
      {% if session.get('user_id') == item.user_id or session.get('role')=='admin' %}
      <a href="/edit/{{item.id}}" class="btn btn-secondary"><i class="fa-solid fa-pen"></i> Edit</a>
      <a href="/delete/{{item.id}}" class="btn btn-danger" onclick="return confirm('Delete this item?')"><i class="fa-solid fa-trash"></i> Delete</a>
      {% endif %}
    </div>
  </div>

  {% if claims %}
  <div class="form-card fade-up fade-up-2" style="margin-top:1.5rem">
    <p style="font-family:'Syne',sans-serif;font-weight:700;margin-bottom:1rem">Claims ({{claims|length}})</p>
    {% for cl in claims %}
    <div style="padding:.8rem;background:var(--surface);border-radius:10px;margin-bottom:.7rem;display:flex;justify-content:space-between;align-items:center;gap:1rem;">
      <div>
        <p style="font-weight:600;font-size:.9rem">{{cl.full_name}}</p>
        <p style="color:var(--muted);font-size:.82rem">{{cl.message or 'No message'}}</p>
        <p style="color:var(--muted);font-size:.78rem;margin-top:.3rem">{{cl.created}}</p>
      </div>
      <span class="chip {{'chip-open' if cl.status=='pending' else ('chip-found' if cl.status=='approved' else 'chip-lost')}}">{{cl.status}}</span>
    </div>
    {% endfor %}
  </div>
  {% endif %}
</div>
{% endblock %}""")

@app.route('/item/<int:item_id>')
@login_required
def item_detail(item_id):
    conn = get_db()
    item = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    claims = conn.execute("""SELECT c.*,u.full_name FROM claims c JOIN users u ON c.user_id=u.id
                             WHERE c.item_id=? ORDER BY c.created DESC""", (item_id,)).fetchall()
    conn.close()
    if not item:
        flash('Item not found.', 'danger')
        return redirect(url_for('search'))
    return render_template_string(DETAIL_HTML, item=item, claims=claims)

# ── CLAIM ──
CLAIM_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """{% block content %}
<div class="page-sm">
  <div class="form-card fade-up">
    <div class="form-title"><i class="fa-solid fa-hand" style="color:var(--green)"></i> Claim Item</div>
    <p class="form-subtitle">You're claiming: <strong>{{item.item_name}}</strong></p>
    <form method="POST" action="/claim/{{item.id}}">
      <div class="field">
        <label>Message to Owner (optional)</label>
        <textarea name="message" placeholder="Describe how you can prove ownership or provide any identifying info…"></textarea>
      </div>
      <div style="display:flex;gap:.8rem">
        <button type="submit" class="btn btn-success"><i class="fa-solid fa-check"></i> Submit Claim</button>
        <a href="/item/{{item.id}}" class="btn btn-secondary">Cancel</a>
      </div>
    </form>
  </div>
</div>
{% endblock %}""")

@app.route('/claim/<int:item_id>', methods=['GET','POST'])
@login_required
def claim(item_id):
    conn = get_db()
    item = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not item:
        flash('Item not found.', 'danger')
        return redirect(url_for('search'))
    if request.method == 'POST':
        msg = request.form.get('message','')
        conn.execute("INSERT INTO claims(item_id,user_id,message) VALUES(?,?,?)",
                     (item_id, session['user_id'], msg))
        conn.commit()
        conn.close()
        flash('Claim submitted! The reporter will be notified.', 'success')
        return redirect(url_for('item_detail', item_id=item_id))
    conn.close()
    return render_template_string(CLAIM_HTML, item=item)

# ── EDIT ITEM ──
EDIT_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """{% block content %}
<div class="page" style="max-width:820px">
  <div class="section-header fade-up">
    <div class="section-title">Edit Item</div>
    <a href="/item/{{item.id}}" class="btn btn-secondary btn-sm"><i class="fa-solid fa-arrow-left"></i> Back</a>
  </div>
  <div class="form-card fade-up fade-up-1">
    <form method="POST" action="/edit/{{item.id}}">
      <div class="form-row">
        <div class="field"><label>Type</label>
          <select name="type">
            <option value="lost" {{'selected' if item.type=='lost' else ''}}>Lost</option>
            <option value="found" {{'selected' if item.type=='found' else ''}}>Found</option>
          </select>
        </div>
        <div class="field"><label>Status</label>
          <select name="status">
            <option value="open" {{'selected' if item.status=='open' else ''}}>Open</option>
            <option value="claimed" {{'selected' if item.status=='claimed' else ''}}>Claimed</option>
            <option value="closed" {{'selected' if item.status=='closed' else ''}}>Closed</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="field"><label>Item Name</label><input name="item_name" value="{{item.item_name}}" required></div>
        <div class="field"><label>Category</label>
          <select name="category">
            {% for cat in ['Mobile Phone','Earphones / AirPods','Charger / Adapter','Smart Watch','USB Drive','Calculator','Laptop','Tablet / iPad','Camera','Other Electronic'] %}
            <option {{'selected' if item.category==cat else ''}}>{{cat}}</option>
            {% endfor %}
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="field"><label>Brand</label><input name="brand" value="{{item.brand or ''}}"></div>
        <div class="field"><label>Color</label><input name="color" value="{{item.color or ''}}"></div>
      </div>
      <div class="field"><label>Location</label><input name="location" value="{{item.location}}" required></div>
      <div class="field"><label>Description</label><textarea name="description">{{item.description or ''}}</textarea></div>
      <button type="submit" class="btn btn-primary"><i class="fa-solid fa-floppy-disk"></i> Save Changes</button>
    </form>
  </div>
</div>
{% endblock %}""")

@app.route('/edit/<int:item_id>', methods=['GET','POST'])
@login_required
def edit_item(item_id):
    conn = get_db()
    item = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not item:
        flash('Item not found.', 'danger')
        return redirect(url_for('dashboard'))
    if session.get('role') != 'admin' and item['user_id'] != session['user_id']:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        f = request.form
        conn.execute("""UPDATE items SET type=?,status=?,item_name=?,category=?,brand=?,color=?,
                     location=?,description=? WHERE id=?""",
                     (f['type'],f['status'],f['item_name'],f['category'],
                      f.get('brand',''),f.get('color',''),f['location'],
                      f.get('description',''), item_id))
        conn.commit()
        conn.close()
        flash('Item updated successfully.', 'success')
        return redirect(url_for('item_detail', item_id=item_id))
    conn.close()
    return render_template_string(EDIT_HTML, item=item)

@app.route('/delete/<int:item_id>')
@login_required
def delete_item(item_id):
    conn = get_db()
    item = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if item and (session.get('role') == 'admin' or item['user_id'] == session['user_id']):
        conn.execute("DELETE FROM claims WHERE item_id=?", (item_id,))
        conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        conn.commit()
        flash('Item deleted.', 'success')
    else:
        flash('Access denied.', 'danger')
    conn.close()
    return redirect(url_for('dashboard'))

# ── PROFILE ──
PROFILE_HTML = BASE_HTML.replace('{% block content %}{% endblock %}', """{% block content %}
<div class="page" style="max-width:820px">
  <div class="section-title fade-up" style="margin-bottom:1.5rem">My Profile</div>
  <div style="display:grid;grid-template-columns:1fr 2fr;gap:1.5rem" class="fade-up fade-up-1">
    <div class="card" style="text-align:center;padding:2rem">
      <div style="width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,var(--accent),var(--accent2));
        margin:0 auto 1rem;display:flex;align-items:center;justify-content:center;font-family:'Syne',sans-serif;
        font-size:2rem;font-weight:800;color:#000">{{user.full_name[0]}}</div>
      <p style="font-family:'Syne',sans-serif;font-weight:700;font-size:1.1rem">{{user.full_name}}</p>
      <p style="color:var(--muted);font-size:.85rem">@{{user.username}}</p>
      <span class="chip {{'chip-found' if user.role=='admin' else 'chip-open'}}" style="margin-top:.8rem">{{user.role|upper}}</span>
    </div>
    <div style="display:flex;flex-direction:column;gap:1.2rem">
      <div class="card">
        <p style="font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin-bottom:.8rem">Account Info</p>
        <div class="detail-grid">
          <div class="detail-item"><label>Email</label><p>{{user.email or '—'}}</p></div>
          <div class="detail-item"><label>Member Since</label><p>{{user.created[:10]}}</p></div>
        </div>
      </div>
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
          <p style="font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)">My Reports</p>
          <a href="/report" class="btn btn-primary btn-sm"><i class="fa-solid fa-plus"></i> New Report</a>
        </div>
        {% if my_items %}
        {% for item in my_items %}
        <div style="display:flex;justify-content:space-between;align-items:center;padding:.7rem 0;border-bottom:1px solid var(--border)">
          <div>
            <p style="font-size:.9rem;font-weight:600">{{item.item_name}}</p>
            <p style="font-size:.78rem;color:var(--muted)">{{item.category}} &bull; {{item.date_reported}}</p>
          </div>
          <div style="display:flex;align-items:center;gap:.5rem">
            <span class="chip {{'chip-lost' if item.type=='lost' else 'chip-found'}}">{{item.type}}</span>
            <a href="/item/{{item.id}}" class="btn btn-secondary btn-sm">View</a>
          </div>
        </div>
        {% endfor %}
        {% else %}
        <p style="color:var(--muted);font-size:.88rem">No items reported yet.</p>
        {% endif %}
      </div>
    </div>
  </div>
</div>
{% endblock %}""")

@app.route('/profile')
@login_required
def profile():
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    my_items = conn.execute("SELECT * FROM items WHERE user_id=? ORDER BY created DESC", (session['user_id'],)).fetchall()
    conn.close()
    return render_template_string(PROFILE_HTML, user=user, my_items=my_items)

# ─────────────────────────────────────────────
#  ADMIN ROUTES
# ─────────────────────────────────────────────
ADMIN_LAYOUT = BASE_HTML.replace('{% block content %}{% endblock %}', """{% block content %}
<div class="admin-aside">
  <p class="aside-label">Dashboard</p>
  <a href="/admin" {% if admin_tab=='overview' %}class="active"{% endif %}><i class="fa-solid fa-chart-pie" style="width:16px"></i> Overview</a>
  <p class="aside-label">Management</p>
  <a href="/admin/items" {% if admin_tab=='items' %}class="active"{% endif %}><i class="fa-solid fa-box-archive" style="width:16px"></i> All Items</a>
  <a href="/admin/users" {% if admin_tab=='users' %}class="active"{% endif %}><i class="fa-solid fa-users" style="width:16px"></i> Users</a>
  <a href="/admin/claims" {% if admin_tab=='claims' %}class="active"{% endif %}><i class="fa-solid fa-hand-holding" style="width:16px"></i> Claims</a>
  <p class="aside-label">Actions</p>
  <a href="/report"><i class="fa-solid fa-plus" style="width:16px"></i> Add Item</a>
  <a href="/dashboard"><i class="fa-solid fa-house" style="width:16px"></i> Back to Portal</a>
</div>
<div class="admin-main">
  {% block admin_content %}{% endblock %}
</div>
{% endblock %}""")

ADMIN_OVERVIEW = ADMIN_LAYOUT.replace('{% block admin_content %}{% endblock %}', """{% block admin_content %}
<div style="margin-bottom:2rem">
  <h2 style="font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:800;margin-bottom:.3rem">Admin Dashboard</h2>
  <p style="color:var(--muted);font-size:.88rem">System overview and quick statistics</p>
</div>

<div class="stats-bar fade-up" style="margin-bottom:2rem">
  <div class="stat-cell"><div class="stat-num">{{stats.total}}</div><div class="stat-lbl">Total Items</div></div>
  <div class="stat-cell"><div class="stat-num" style="color:#f08060">{{stats.lost}}</div><div class="stat-lbl">Lost</div></div>
  <div class="stat-cell"><div class="stat-num" style="color:var(--green)">{{stats.found}}</div><div class="stat-lbl">Found</div></div>
  <div class="stat-cell"><div class="stat-num" style="color:var(--blue)">{{stats.users}}</div><div class="stat-lbl">Users</div></div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem">
  <div class="card fade-up fade-up-1">
    <p style="font-family:'Syne',sans-serif;font-weight:700;margin-bottom:1rem">Category Breakdown</p>
    {% for row in cat_stats %}
    <div style="display:flex;justify-content:space-between;align-items:center;padding:.5rem 0;border-bottom:1px solid var(--border)">
      <span style="font-size:.88rem">{{row.category}}</span>
      <span class="chip chip-cat">{{row.cnt}}</span>
    </div>
    {% endfor %}
  </div>
  <div class="card fade-up fade-up-2">
    <p style="font-family:'Syne',sans-serif;font-weight:700;margin-bottom:1rem">Recent Activity</p>
    {% for item in recent %}
    <div style="padding:.6rem 0;border-bottom:1px solid var(--border)">
      <div style="display:flex;gap:.5rem;align-items:center">
        <span class="chip {{'chip-lost' if item.type=='lost' else 'chip-found'}}" style="font-size:.7rem">{{item.type}}</span>
        <span style="font-size:.88rem;font-weight:600">{{item.item_name}}</span>
      </div>
      <span style="font-size:.78rem;color:var(--muted)">{{item.location}} &bull; {{item.date_reported}}</span>
    </div>
    {% endfor %}
  </div>
</div>
{% endblock %}""")

@app.route('/admin')
@admin_required
def admin_overview():
    conn = get_db()
    stats = {
        'total': conn.execute("SELECT COUNT(*) FROM items").fetchone()[0],
        'lost':  conn.execute("SELECT COUNT(*) FROM items WHERE type='lost'").fetchone()[0],
        'found': conn.execute("SELECT COUNT(*) FROM items WHERE type='found'").fetchone()[0],
        'users': conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
    }
    cat_stats = conn.execute("SELECT category, COUNT(*) as cnt FROM items GROUP BY category ORDER BY cnt DESC").fetchall()
    recent = conn.execute("SELECT * FROM items ORDER BY created DESC LIMIT 8").fetchall()
    conn.close()
    return render_template_string(ADMIN_OVERVIEW, stats=stats, cat_stats=cat_stats, recent=recent, admin_tab='overview')

ADMIN_ITEMS = ADMIN_LAYOUT.replace('{% block admin_content %}{% endblock %}', """{% block admin_content %}
<div class="section-header fade-up">
  <div class="section-title">All Items</div>
  <a href="/report" class="btn btn-primary btn-sm"><i class="fa-solid fa-plus"></i> Add Item</a>
</div>
<div class="tbl-wrap fade-up fade-up-1">
  <table>
    <thead><tr>
      <th>#</th><th>Type</th><th>Category</th><th>Item</th><th>Location</th><th>Reported By</th><th>Status</th><th>Date</th><th>Actions</th>
    </tr></thead>
    <tbody>
    {% for item in items %}
    <tr>
      <td style="color:var(--muted)">{{item.id}}</td>
      <td><span class="chip {{'chip-lost' if item.type=='lost' else 'chip-found'}}">{{item.type}}</span></td>
      <td style="color:var(--muted);font-size:.82rem">{{item.category}}</td>
      <td><strong>{{item.item_name}}</strong>{% if item.brand %}<br><span style="font-size:.78rem;color:var(--muted)">{{item.brand}}</span>{% endif %}</td>
      <td style="font-size:.82rem">{{item.location}}</td>
      <td style="font-size:.82rem">{{item.contact_name}}</td>
      <td><span class="chip {{'chip-open' if item.status=='open' else ('chip-claimed' if item.status=='claimed' else 'chip-closed')}}">{{item.status}}</span></td>
      <td style="font-size:.78rem;color:var(--muted)">{{item.date_reported}}</td>
      <td>
        <div style="display:flex;gap:.4rem">
          <a href="/item/{{item.id}}" class="btn btn-secondary btn-sm"><i class="fa-solid fa-eye"></i></a>
          <a href="/edit/{{item.id}}" class="btn btn-secondary btn-sm"><i class="fa-solid fa-pen"></i></a>
          <a href="/delete/{{item.id}}" class="btn btn-danger btn-sm" onclick="return confirm('Delete?')"><i class="fa-solid fa-trash"></i></a>
        </div>
      </td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}""")

@app.route('/admin/items')
@admin_required
def admin_items():
    conn = get_db()
    items = conn.execute("SELECT * FROM items ORDER BY created DESC").fetchall()
    conn.close()
    return render_template_string(ADMIN_ITEMS, items=items, admin_tab='items')

ADMIN_USERS = ADMIN_LAYOUT.replace('{% block admin_content %}{% endblock %}', """{% block admin_content %}
<div class="section-header fade-up">
  <div class="section-title">All Users</div>
  <span style="color:var(--muted);font-size:.88rem">{{users|length}} registered users</span>
</div>
<div class="tbl-wrap fade-up fade-up-1">
  <table>
    <thead><tr>
      <th>#</th><th>Name</th><th>Username</th><th>Email</th><th>Role</th><th>Joined</th><th>Items</th><th>Actions</th>
    </tr></thead>
    <tbody>
    {% for u in users %}
    <tr>
      <td style="color:var(--muted)">{{u.id}}</td>
      <td><strong>{{u.full_name}}</strong></td>
      <td style="color:var(--muted)">@{{u.username}}</td>
      <td style="font-size:.82rem">{{u.email or '—'}}</td>
      <td><span class="chip {{'chip-found' if u.role=='admin' else 'chip-open'}}">{{u.role}}</span></td>
      <td style="font-size:.78rem;color:var(--muted)">{{u.created[:10]}}</td>
      <td style="text-align:center">{{u.item_count}}</td>
      <td>
        {% if u.role != 'admin' %}
        <a href="/admin/promote/{{u.id}}" class="btn btn-success btn-sm" onclick="return confirm('Promote to admin?')">
          <i class="fa-solid fa-arrow-up"></i> Promote
        </a>
        <a href="/admin/delete_user/{{u.id}}" class="btn btn-danger btn-sm" onclick="return confirm('Delete user?')">
          <i class="fa-solid fa-trash"></i>
        </a>
        {% else %}
        <span style="color:var(--muted);font-size:.8rem">Protected</span>
        {% endif %}
      </td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}""")

@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db()
    users = conn.execute("""SELECT u.*, COUNT(i.id) as item_count
                            FROM users u LEFT JOIN items i ON i.user_id=u.id
                            GROUP BY u.id ORDER BY u.created DESC""").fetchall()
    conn.close()
    return render_template_string(ADMIN_USERS, users=users, admin_tab='users')

@app.route('/admin/promote/<int:uid>')
@admin_required
def admin_promote(uid):
    conn = get_db()
    conn.execute("UPDATE users SET role='admin' WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    flash('User promoted to admin.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_user/<int:uid>')
@admin_required
def admin_delete_user(uid):
    if uid == session['user_id']:
        flash("Can't delete yourself.", 'danger')
        return redirect(url_for('admin_users'))
    conn = get_db()
    conn.execute("DELETE FROM claims WHERE user_id=?", (uid,))
    conn.execute("UPDATE items SET user_id=NULL WHERE user_id=?", (uid,))
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    flash('User deleted.', 'success')
    return redirect(url_for('admin_users'))

ADMIN_CLAIMS = ADMIN_LAYOUT.replace('{% block admin_content %}{% endblock %}', """{% block admin_content %}
<div class="section-header fade-up">
  <div class="section-title">Claims Management</div>
  <span style="color:var(--muted);font-size:.88rem">{{claims|length}} total claims</span>
</div>
<div class="tbl-wrap fade-up fade-up-1">
  <table>
    <thead><tr>
      <th>#</th><th>Item</th><th>Claimant</th><th>Message</th><th>Status</th><th>Date</th><th>Actions</th>
    </tr></thead>
    <tbody>
    {% for cl in claims %}
    <tr>
      <td style="color:var(--muted)">{{cl.id}}</td>
      <td><a href="/item/{{cl.item_id}}" style="color:var(--accent);text-decoration:none">{{cl.item_name}}</a></td>
      <td>{{cl.full_name}}</td>
      <td style="font-size:.82rem;color:var(--muted);max-width:200px">{{cl.message or '—'}}</td>
      <td>
        <span class="chip {{'chip-open' if cl.status=='pending' else ('chip-found' if cl.status=='approved' else 'chip-lost')}}">
          {{cl.status}}
        </span>
      </td>
      <td style="font-size:.78rem;color:var(--muted)">{{cl.created[:10]}}</td>
      <td>
        <div style="display:flex;gap:.4rem">
          {% if cl.status=='pending' %}
          <a href="/admin/claim/{{cl.id}}/approve" class="btn btn-success btn-sm"><i class="fa-solid fa-check"></i> Approve</a>
          <a href="/admin/claim/{{cl.id}}/reject" class="btn btn-danger btn-sm"><i class="fa-solid fa-xmark"></i> Reject</a>
          {% else %}
          <span style="color:var(--muted);font-size:.8rem">Resolved</span>
          {% endif %}
        </div>
      </td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}""")

@app.route('/admin/claims')
@admin_required
def admin_claims():
    conn = get_db()
    claims = conn.execute("""SELECT c.*,u.full_name,i.item_name FROM claims c
                             JOIN users u ON c.user_id=u.id
                             JOIN items i ON c.item_id=i.id
                             ORDER BY c.created DESC""").fetchall()
    conn.close()
    return render_template_string(ADMIN_CLAIMS, claims=claims, admin_tab='claims')

@app.route('/admin/claim/<int:cid>/<action>')
@admin_required
def admin_claim_action(cid, action):
    conn = get_db()
    if action == 'approve':
        conn.execute("UPDATE claims SET status='approved' WHERE id=?", (cid,))
        cl = conn.execute("SELECT item_id FROM claims WHERE id=?", (cid,)).fetchone()
        if cl:
            conn.execute("UPDATE items SET status='claimed' WHERE id=?", (cl['item_id'],))
        flash('Claim approved and item marked as claimed.', 'success')
    elif action == 'reject':
        conn.execute("UPDATE claims SET status='rejected' WHERE id=?", (cid,))
        flash('Claim rejected.', 'warning')
    conn.commit()
    conn.close()
    return redirect(url_for('admin_claims'))

# ─────────────────────────────────────────────
#  API ENDPOINTS (JSON)
# ─────────────────────────────────────────────
@app.route('/api/stats')
def api_stats():
    conn = get_db()
    data = {
        'total': conn.execute("SELECT COUNT(*) FROM items").fetchone()[0],
        'lost':  conn.execute("SELECT COUNT(*) FROM items WHERE type='lost'").fetchone()[0],
        'found': conn.execute("SELECT COUNT(*) FROM items WHERE type='found'").fetchone()[0],
        'open':  conn.execute("SELECT COUNT(*) FROM items WHERE status='open'").fetchone()[0],
    }
    conn.close()
    return jsonify(data)

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("\n" + "="*55)
    print("  🎓 CampusTrace — Lost & Found System")
    print("="*55)
    print("  URL   : http://localhost:5000")
    print("  Admin : admin / admin123")
    print("  Student: student1 / pass123")
    print("="*55 + "\n")
    app.run(debug=True, port=5000)
