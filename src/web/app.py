"""
Web Dashboard - Flask Application
"""
import os
import json
import secrets
import requests
from functools import wraps
from flask import Flask, render_template_string, request, jsonify, redirect, session, url_for
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

DISCORD_CLIENT_ID = os.getenv("CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:5000/callback")
DISCORD_API_BASE = "https://discord.com/api/v10"
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Import utils
import sys
sys.path.insert(0, str(BASE_DIR / "src"))
from utils.config import load_config, save_config, get_text
from utils.database import get_all_tickets, get_stats, get_logs, get_connection
from utils.backup import get_backups

def get_discord_auth_url():
    return f"{DISCORD_API_BASE}/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify%20guilds"

def exchange_code(code):
    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "scope": "identify guilds"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(f"{DISCORD_API_BASE}/oauth2/token", data=data, headers=headers)
    return r.json()

def get_user(token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{DISCORD_API_BASE}/users/@me", headers=headers)
    return r.json()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "discord_token" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# CSS Global
DASHBOARD_CSS = """
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
        min-height: 100vh;
        color: #e0e0e0;
    }
    .navbar {
        background: rgba(88, 101, 242, 0.15);
        backdrop-filter: blur(20px);
        border-bottom: 1px solid rgba(88, 101, 242, 0.3);
        padding: 15px 30px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .navbar-brand {
        font-size: 24px;
        font-weight: 700;
        color: #5865F2;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .navbar-user {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .user-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        border: 2px solid #5865F2;
    }
    .sidebar {
        width: 260px;
        background: rgba(255,255,255,0.03);
        border-right: 1px solid rgba(255,255,255,0.08);
        min-height: calc(100vh - 70px);
        padding: 20px;
        position: fixed;
    }
    .sidebar-item {
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 8px;
        cursor: pointer;
        transition: all 0.3s;
        display: flex;
        align-items: center;
        gap: 12px;
        color: #aaa;
        text-decoration: none;
    }
    .sidebar-item:hover, .sidebar-item.active {
        background: rgba(88, 101, 242, 0.2);
        color: #fff;
    }
    .main-content {
        margin-left: 260px;
        padding: 30px;
    }
    .card {
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    }
    .card-header {
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 20px;
        color: #fff;
    }
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin-bottom: 30px;
    }
    .stat-card {
        background: rgba(88, 101, 242, 0.15);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(88, 101, 242, 0.3);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        transition: transform 0.3s;
    }
    .stat-card:hover {
        transform: translateY(-5px);
    }
    .stat-value {
        font-size: 32px;
        font-weight: 700;
        color: #5865F2;
    }
    .stat-label {
        font-size: 13px;
        color: #888;
        margin-top: 5px;
    }
    .btn {
        padding: 10px 20px;
        border-radius: 10px;
        border: none;
        cursor: pointer;
        font-weight: 600;
        transition: all 0.3s;
        text-decoration: none;
        display: inline-block;
    }
    .btn-primary {
        background: linear-gradient(135deg, #5865F2, #4752C4);
        color: #fff;
    }
    .btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(88, 101, 242, 0.4);
    }
    .btn-danger {
        background: linear-gradient(135deg, #ED4245, #C03537);
        color: #fff;
    }
    .btn-success {
        background: linear-gradient(135deg, #57F287, #3BA55D);
        color: #fff;
    }
    .form-group {
        margin-bottom: 20px;
    }
    .form-label {
        display: block;
        margin-bottom: 8px;
        font-weight: 500;
        color: #ccc;
    }
    .form-input, .form-select, .form-textarea {
        width: 100%;
        padding: 12px 16px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.1);
        background: rgba(255,255,255,0.05);
        color: #fff;
        font-size: 14px;
        transition: all 0.3s;
    }
    .form-input:focus, .form-select:focus, .form-textarea:focus {
        outline: none;
        border-color: #5865F2;
        box-shadow: 0 0 0 3px rgba(88, 101, 242, 0.2);
    }
    .form-textarea {
        min-height: 100px;
        resize: vertical;
    }
    .table {
        width: 100%;
        border-collapse: collapse;
    }
    .table th, .table td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    .table th {
        font-weight: 600;
        color: #888;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .table tr:hover {
        background: rgba(255,255,255,0.02);
    }
    .badge {
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-open { background: rgba(87, 242, 135, 0.2); color: #57F287; }
    .badge-closed { background: rgba(237, 66, 69, 0.2); color: #ED4245; }
    .badge-claimed { background: rgba(88, 101, 242, 0.2); color: #5865F2; }
    .preview-box {
        background: rgba(0,0,0,0.3);
        border-radius: 12px;
        padding: 20px;
        margin-top: 15px;
    }
    .preview-embed {
        background: rgba(88, 101, 242, 0.1);
        border-left: 4px solid #5865F2;
        border-radius: 8px;
        padding: 15px;
    }
    .preview-title {
        font-weight: 700;
        color: #fff;
        margin-bottom: 8px;
    }
    .preview-desc {
        color: #ccc;
        line-height: 1.5;
    }
    .preview-footer {
        margin-top: 10px;
        font-size: 12px;
        color: #888;
    }
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
    }
    .login-card {
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 24px;
        padding: 50px;
        text-align: center;
        max-width: 400px;
        width: 90%;
    }
    .login-logo {
        font-size: 48px;
        margin-bottom: 20px;
    }
    .login-title {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .login-subtitle {
        color: #888;
        margin-bottom: 30px;
    }
    .discord-btn {
        background: linear-gradient(135deg, #5865F2, #4752C4);
        color: #fff;
        padding: 15px 30px;
        border-radius: 12px;
        border: none;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        width: 100%;
        transition: all 0.3s;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        text-decoration: none;
    }
    .discord-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(88, 101, 242, 0.4);
    }
    .grid-2 {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
    }
    .grid-3 {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 20px;
    }
    @media (max-width: 768px) {
        .sidebar { display: none; }
        .main-content { margin-left: 0; }
        .grid-2, .grid-3 { grid-template-columns: 1fr; }
    }
</style>
"""

# Template base
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Ticket Pro</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    """ + DASHBOARD_CSS + """
</head>
<body>
    <div class="navbar">
        <div class="navbar-brand">
            <i class="fas fa-ticket-alt"></i> Ticket Pro
        </div>
        <div class="navbar-user">
            <span>{{ user.get('username', 'User') if user else 'Guest' }}</span>
            {% if user %}
            <img src="https://cdn.discordapp.com/avatars/{{ user.id }}/{{ user.avatar }}.png" class="user-avatar" alt="Avatar">
            <a href="/logout" class="btn btn-danger">Sair</a>
            {% endif %}
        </div>
    </div>

    <div class="sidebar">
        <a href="/dashboard" class="sidebar-item {% if active == 'dashboard' %}active{% endif %}">
            <i class="fas fa-chart-line"></i> Dashboard
        </a>
        <a href="/tickets" class="sidebar-item {% if active == 'tickets' %}active{% endif %}">
            <i class="fas fa-ticket-alt"></i> Tickets
        </a>
        <a href="/settings" class="sidebar-item {% if active == 'settings' %}active{% endif %}">
            <i class="fas fa-cog"></i> Configurações
        </a>
        <a href="/logs" class="sidebar-item {% if active == 'logs' %}active{% endif %}">
            <i class="fas fa-history"></i> Logs
        </a>
        <a href="/backups" class="sidebar-item {% if active == 'backups' %}active{% endif %}">
            <i class="fas fa-database"></i> Backups
        </a>
    </div>

    <div class="main-content">
        {{ content | safe }}
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    if "discord_token" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login")
def login():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Login - Ticket Pro</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        """ + DASHBOARD_CSS + """
    </head>
    <body>
        <div class="login-container">
            <div class="login-card">
                <div class="login-logo">🎫</div>
                <div class="login-title">Ticket Pro</div>
                <div class="login-subtitle">Painel de Administração</div>
                <a href="{{ auth_url }}" class="discord-btn">
                    <i class="fab fa-discord"></i> Entrar com Discord
                </a>
            </div>
        </div>
    </body>
    </html>
    """, auth_url=get_discord_auth_url())

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect(url_for("login"))

    token_data = exchange_code(code)
    if "access_token" not in token_data:
        return redirect(url_for("login"))

    session["discord_token"] = token_data["access_token"]
    user = get_user(token_data["access_token"])
    session["user"] = user

    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    config = load_config()
    stats = get_stats(config.get("guild_id"))
    recent_tickets = get_all_tickets(config.get("guild_id"), limit=10)
    recent_logs = get_logs(config.get("guild_id"), limit=10)

    content = """
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">""" + str(stats["total"]) + """</div>
            <div class="stat-label">Total de Tickets</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">""" + str(stats["open"]) + """</div>
            <div class="stat-label">Tickets Abertos</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">""" + str(stats["closed"]) + """</div>
            <div class="stat-label">Tickets Fechados</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">""" + str(stats["avg_rating"]) + """ ⭐</div>
            <div class="stat-label">Avaliação Média</div>
        </div>
    </div>

    <div class="card">
        <div class="card-header">📋 Tickets Recentes</div>
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Usuário</th>
                    <th>Categoria</th>
                    <th>Status</th>
                    <th>Data</th>
                </tr>
            </thead>
            <tbody>
    """

    for ticket in recent_tickets:
        status_class = f"badge-{ticket['status']}"
        content += f"""
                <tr>
                    <td>#{ticket['id']}</td>
                    <td><@{ticket['user_id']}></td>
                    <td>{ticket['category_id']}</td>
                    <td><span class="badge {status_class}">{ticket['status'].upper()}</span></td>
                    <td>{ticket['created_at']}</td>
                </tr>
        """

    content += """
            </tbody>
        </table>
    </div>

    <div class="card">
        <div class="card-header">📝 Logs Recentes</div>
        <table class="table">
            <thead>
                <tr>
                    <th>Ação</th>
                    <th>Usuário</th>
                    <th>Data</th>
                </tr>
            </thead>
            <tbody>
    """

    for log in recent_logs:
        content += f"""
                <tr>
                    <td>{log['action']}</td>
                    <td><@{log['user_id']}></td>
                    <td>{log['created_at']}</td>
                </tr>
        """

    content += """
            </tbody>
        </table>
    </div>
    """

    return render_template_string(BASE_TEMPLATE, title="Dashboard", user=session.get("user"), active="dashboard", content=content)

@app.route("/tickets")
@login_required
def tickets_page():
    config = load_config()
    all_tickets = get_all_tickets(config.get("guild_id"), limit=100)

    content = """
    <div class="card">
        <div class="card-header">🎫 Todos os Tickets</div>
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Canal</th>
                    <th>Usuário</th>
                    <th>Categoria</th>
                    <th>Status</th>
                    <th>Prioridade</th>
                    <th>Staff</th>
                    <th>Data</th>
                </tr>
            </thead>
            <tbody>
    """

    for ticket in all_tickets:
        status_class = f"badge-{ticket['status']}"
        claimed = f"<@{ticket['claimed_by']}>" if ticket['claimed_by'] else "Nenhum"
        content += f"""
                <tr>
                    <td>#{ticket['id']}</td>
                    <td><#{ticket['channel_id']}></td>
                    <td><@{ticket['user_id']}></td>
                    <td>{ticket['category_id']}</td>
                    <td><span class="badge {status_class}">{ticket['status'].upper()}</span></td>
                    <td>{ticket['priority'].upper()}</td>
                    <td>{claimed}</td>
                    <td>{ticket['created_at']}</td>
                </tr>
        """

    content += """
            </tbody>
        </table>
    </div>
    """

    return render_template_string(BASE_TEMPLATE, title="Tickets", user=session.get("user"), active="tickets", content=content)

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings_page():
    config = load_config()
    message = ""

    if request.method == "POST":
        # Atualizar configurações
        config["bot"]["name"] = request.form.get("bot_name", config["bot"]["name"])
        config["bot"]["status"] = request.form.get("bot_status", config["bot"]["status"])
        config["bot"]["activity_type"] = request.form.get("activity_type", config["bot"]["activity_type"])
        config["bot"]["activity_text"] = request.form.get("activity_text", config["bot"]["activity_text"])
        config["bot"]["main_color"] = request.form.get("main_color", config["bot"]["main_color"])
        config["bot"]["language"] = request.form.get("language", config["bot"]["language"])

        config["embeds"]["panel_title"] = request.form.get("panel_title", config["embeds"]["panel_title"])
        config["embeds"]["panel_description"] = request.form.get("panel_description", config["embeds"]["panel_description"])
        config["embeds"]["panel_color"] = request.form.get("panel_color", config["embeds"]["panel_color"])
        config["embeds"]["panel_footer"] = request.form.get("panel_footer", config["embeds"]["panel_footer"])

        config["tickets"]["cooldown_seconds"] = int(request.form.get("cooldown_seconds", config["tickets"]["cooldown_seconds"]))
        config["tickets"]["max_open_per_user"] = int(request.form.get("max_open_per_user", config["tickets"]["max_open_per_user"]))
        config["tickets"]["require_reason"] = request.form.get("require_reason") == "on"

        save_config(config)
        message = "<div style='background: rgba(87, 242, 135, 0.2); color: #57F287; padding: 15px; border-radius: 12px; margin-bottom: 20px;'>✅ Configurações salvas com sucesso!</div>"

    content = f"""
    {message}
    <form method="POST">
        <div class="card">
            <div class="card-header">🤖 Configurações do Bot</div>
            <div class="grid-2">
                <div class="form-group">
                    <label class="form-label">Nome do Bot</label>
                    <input type="text" name="bot_name" class="form-input" value="{config['bot']['name']}">
                </div>
                <div class="form-group">
                    <label class="form-label">Status</label>
                    <select name="bot_status" class="form-select">
                        <option value="online" {'selected' if config['bot']['status'] == 'online' else ''}>Online</option>
                        <option value="idle" {'selected' if config['bot']['status'] == 'idle' else ''}>Ausente</option>
                        <option value="dnd" {'selected' if config['bot']['status'] == 'dnd' else ''}>Não Perturbar</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Tipo de Atividade</label>
                    <select name="activity_type" class="form-select">
                        <option value="playing" {'selected' if config['bot']['activity_type'] == 'playing' else ''}>Jogando</option>
                        <option value="watching" {'selected' if config['bot']['activity_type'] == 'watching' else ''}>Assistindo</option>
                        <option value="listening" {'selected' if config['bot']['activity_type'] == 'listening' else ''}>Ouvindo</option>
                        <option value="competing" {'selected' if config['bot']['activity_type'] == 'competing' else ''}>Competindo</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Texto da Atividade</label>
                    <input type="text" name="activity_text" class="form-input" value="{config['bot']['activity_text']}">
                </div>
                <div class="form-group">
                    <label class="form-label">Cor Principal</label>
                    <input type="color" name="main_color" class="form-input" value="{config['bot']['main_color']}">
                </div>
                <div class="form-group">
                    <label class="form-label">Idioma</label>
                    <select name="language" class="form-select">
                        <option value="pt" {'selected' if config['bot']['language'] == 'pt' else ''}>Português</option>
                        <option value="en" {'selected' if config['bot']['language'] == 'en' else ''}>English</option>
                    </select>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">🎨 Configurações da Embed</div>
            <div class="grid-2">
                <div class="form-group">
                    <label class="form-label">Título do Painel</label>
                    <input type="text" name="panel_title" class="form-input" value="{config['embeds']['panel_title']}">
                </div>
                <div class="form-group">
                    <label class="form-label">Cor do Painel</label>
                    <input type="color" name="panel_color" class="form-input" value="{config['embeds']['panel_color']}">
                </div>
                <div class="form-group" style="grid-column: 1 / -1;">
                    <label class="form-label">Descrição do Painel</label>
                    <textarea name="panel_description" class="form-textarea">{config['embeds']['panel_description']}</textarea>
                </div>
                <div class="form-group">
                    <label class="form-label">Footer</label>
                    <input type="text" name="panel_footer" class="form-input" value="{config['embeds']['panel_footer']}">
                </div>
            </div>

            <div class="preview-box">
                <div style="font-size: 12px; color: #888; margin-bottom: 10px;">PREVIEW</div>
                <div class="preview-embed">
                    <div class="preview-title">{config['embeds']['panel_title']}</div>
                    <div class="preview-desc">{config['embeds']['panel_description'].replace(chr(10), '<br>')}</div>
                    <div class="preview-footer">{config['embeds']['panel_footer']}</div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">⚙️ Configurações de Tickets</div>
            <div class="grid-3">
                <div class="form-group">
                    <label class="form-label">Cooldown (segundos)</label>
                    <input type="number" name="cooldown_seconds" class="form-input" value="{config['tickets']['cooldown_seconds']}">
                </div>
                <div class="form-group">
                    <label class="form-label">Máx. Tickets por Usuário</label>
                    <input type="number" name="max_open_per_user" class="form-input" value="{config['tickets']['max_open_per_user']}">
                </div>
                <div class="form-group">
                    <label class="form-label">Exigir Motivo</label>
                    <input type="checkbox" name="require_reason" {'checked' if config['tickets']['require_reason'] else ''}>
                </div>
            </div>
        </div>

        <button type="submit" class="btn btn-primary">
            <i class="fas fa-save"></i> Salvar Configurações
        </button>
    </form>
    """

    return render_template_string(BASE_TEMPLATE, title="Configurações", user=session.get("user"), active="settings", content=content)

@app.route("/logs")
@login_required
def logs_page():
    config = load_config()
    logs = get_logs(config.get("guild_id"), limit=100)

    content = """
    <div class="card">
        <div class="card-header">📝 Logs do Sistema</div>
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Ação</th>
                    <th>Usuário</th>
                    <th>Alvo</th>
                    <th>Detalhes</th>
                    <th>Data</th>
                </tr>
            </thead>
            <tbody>
    """

    for log in logs:
        details = json.loads(log["details"]) if log["details"] else {}
        content += f"""
                <tr>
                    <td>#{log['id']}</td>
                    <td>{log['action']}</td>
                    <td><@{log['user_id']}></td>
                    <td><@{log['target_id']}>""" + (f" ({log['target_id']})" if log['target_id'] else "-") + """</td>
                    <td>{json.dumps(details, ensure_ascii=False)[:100]}</td>
                    <td>{log['created_at']}</td>
                </tr>
        """

    content += """
            </tbody>
        </table>
    </div>
    """

    return render_template_string(BASE_TEMPLATE, title="Logs", user=session.get("user"), active="logs", content=content)

@app.route("/backups")
@login_required
def backups_page():
    backups = get_backups()

    content = """
    <div class="card">
        <div class="card-header">💾 Backups</div>
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Arquivo</th>
                    <th>Tamanho</th>
                    <th>Data</th>
                </tr>
            </thead>
            <tbody>
    """

    for backup in backups:
        size_mb = backup[2] / (1024 * 1024)
        content += f"""
                <tr>
                    <td>#{backup[0]}</td>
                    <td>{backup[1]}</td>
                    <td>{size_mb:.2f} MB</td>
                    <td>{backup[3]}</td>
                </tr>
        """

    content += """
            </tbody>
        </table>
    </div>
    """

    return render_template_string(BASE_TEMPLATE, title="Backups", user=session.get("user"), active="backups", content=content)

# API Endpoints
@app.route("/api/stats")
@login_required
def api_stats():
    config = load_config()
    return jsonify(get_stats(config.get("guild_id")))

@app.route("/api/tickets")
@login_required
def api_tickets():
    config = load_config()
    return jsonify(get_all_tickets(config.get("guild_id"), limit=100))

@app.route("/api/config", methods=["GET", "POST"])
@login_required
def api_config():
    if request.method == "POST":
        new_config = request.json
        save_config(new_config)
        return jsonify({"success": True, "message": "Configuração salva!"})
    return jsonify(load_config())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
