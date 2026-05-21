"""
Transcript Generator
"""
import datetime
import html
import json
import os
from pathlib import Path

if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_SERVICE_NAME"):
    BASE_DIR = Path("/data")
else:
    BASE_DIR = Path(__file__).parent.parent.parent

TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

def generate_transcript_html(ticket_data, messages, guild_name="Servidor"):
    """Generate HTML transcript for a ticket"""

    ticket = ticket_data
    msg_list = messages

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcript - Ticket #{ticket['id']}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: rgba(88, 101, 242, 0.15);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(88, 101, 242, 0.3);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        .header h1 {{
            font-size: 28px;
            color: #5865F2;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .ticket-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .info-item {{
            background: rgba(255,255,255,0.05);
            padding: 12px 16px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .info-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            margin-bottom: 4px;
        }}
        .info-value {{
            font-size: 14px;
            font-weight: 600;
            color: #fff;
        }}
        .status-open {{ color: #57F287; }}
        .status-closed {{ color: #ED4245; }}
        .status-claimed {{ color: #5865F2; }}
        .messages {{
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.08);
            overflow: hidden;
        }}
        .message {{
            padding: 16px 24px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            transition: background 0.2s;
        }}
        .message:hover {{
            background: rgba(255,255,255,0.03);
        }}
        .message-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 8px;
        }}
        .avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #5865F2, #EB459E);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 16px;
            color: #fff;
        }}
        .author-name {{
            font-weight: 600;
            color: #fff;
            font-size: 15px;
        }}
        .timestamp {{
            font-size: 12px;
            color: #666;
        }}
        .message-content {{
            margin-left: 52px;
            color: #ccc;
            line-height: 1.6;
            word-wrap: break-word;
        }}
        .message-content img {{
            max-width: 100%;
            border-radius: 8px;
            margin-top: 8px;
        }}
        .attachments {{
            margin-left: 52px;
            margin-top: 8px;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .attachment {{
            background: rgba(88, 101, 242, 0.2);
            border: 1px solid rgba(88, 101, 242, 0.4);
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 12px;
            color: #aab2ff;
        }}
        .footer {{
            text-align: center;
            padding: 30px;
            color: #555;
            font-size: 13px;
        }}
        .footer i {{
            color: #5865F2;
        }}
        @media print {{
            body {{ background: #fff; color: #000; }}
            .header {{ background: #f0f0f0; border: 1px solid #ccc; }}
            .messages {{ background: #fff; border: 1px solid #ccc; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1><i class="fas fa-ticket-alt"></i> Transcript - Ticket #{ticket['id']}</h1>
            <div class="ticket-info">
                <div class="info-item">
                    <div class="info-label">Servidor</div>
                    <div class="info-value">{html.escape(guild_name)}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Categoria</div>
                    <div class="info-value">{html.escape(str(ticket['category_id']))}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Status</div>
                    <div class="info-value status-{ticket['status'].lower()}">{ticket['status'].upper()}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Prioridade</div>
                    <div class="info-value">{html.escape(str(ticket['priority']))}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Criado em</div>
                    <div class="info-value">{ticket['created_at']}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Mensagens</div>
                    <div class="info-value">{ticket['message_count']}</div>
                </div>
            </div>
        </div>
        <div class="messages">
"""

    for msg in msg_list:
        avatar_letter = msg["author_name"][0].upper() if msg["author_name"] else "?"
        content = html.escape(msg["content"] or "").replace("\n", "<br>")

        attachments_html = ""
        if msg.get("attachments"):
            attachments_html = '<div class="attachments">' + ''.join([
                f'<span class="attachment"><i class="fas fa-paperclip"></i> {html.escape(str(a))}</span>' 
                for a in msg["attachments"]
            ]) + '</div>'

        html_content += f"""
            <div class="message">
                <div class="message-header">
                    <div class="avatar">{avatar_letter}</div>
                    <div>
                        <div class="author-name">{html.escape(msg["author_name"] or "Desconhecido")}</div>
                        <div class="timestamp">{msg["created_at"]}</div>
                    </div>
                </div>
                <div class="message-content">{content}</div>
                {attachments_html}
            </div>
"""

    html_content += f"""
        </div>
        <div class="footer">
            <i class="fas fa-ticket-alt"></i> Ticket Pro System — Gerado em {datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
        </div>
    </div>
</body>
</html>"""

    return html_content

def save_transcript(ticket_id, html_content):
    """Save transcript to file"""
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"transcript_{ticket_id}_{int(datetime.datetime.now().timestamp())}.html"
    filepath = TRANSCRIPTS_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(filepath)
