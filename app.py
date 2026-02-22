from flask import Flask, render_template, redirect, url_for
import requests, os
from requests.auth import HTTPDigestAuth
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()

# CONFIGURAÇÃO DVR
DVR_IP = os.getenv('DVR_IP')
DVR_USER = os.getenv('DVR_USER')
DVR_PASS = os.getenv('DVR_PASS')
CHANNELS = [0, 1, 2, 3]

def send_config(command):
    url = f"http://{DVR_IP}/cgi-bin/configManager.cgi?action=setConfig&{command}"
    return requests.get(url, auth=HTTPDigestAuth(DVR_USER, DVR_PASS))

def aplicar_24h():
    for ch in CHANNELS:
        base = f"MotionDetect[{ch}]"

        send_config(f"{base}.Enable=enable")
        send_config(f"{base}.EventHandler.MailEnable=true")
        send_config(f"{base}.EventHandler.BeepEnable=true")

        for day in range(8):
            for slot in range(6):
                send_config(f"{base}.EventHandler.TimeSection[{day}][{slot}]=0 00:00:00-24:00:00")

def desativar_total():
    for ch in CHANNELS:
        base = f"MotionDetect[{ch}]"

        send_config(f"{base}.Enable=false")
        send_config(f"{base}.EventHandler.MailEnable=false")
        send_config(f"{base}.EventHandler.BeepEnable=false")

        for day in range(8):
            for slot in range(6):
                send_config(f"{base}.EventHandler.TimeSection[{day}][{slot}]=0 00:00:00-24:00:00")

def aplicar_madrugada():
    # Agenda: 22:00 às 06:30
    # Intelbras usa tabela de horário semanal
    for ch in CHANNELS:
        base = f"MotionDetect[{ch}]"

        # Ativa recurso
        send_config(f"{base}.Enable=true")

        # Segunda a Domingo
        for day in range(6):
            send_config(f"{base}.EventHandler.TimeSection[{day}][0]=1 22:00:00-23:59:59")
            send_config(f"{base}.EventHandler.TimeSection[{day}][1]=1 00:00:00-06:30:00")
            # send_config(f"{base}.Schedule[{ch}][{day}].StartTime=00:00")
            # send_config(f"{base}.Schedule[{ch}][{day}].EndTime=06:30")

        send_config(f"{base}.EventHandler.EmailEnable=true")
        send_config(f"{base}.EventHandler.BuzzerEnable=true")

def get_config(name):
    url = f"http://{DVR_IP}/cgi-bin/configManager.cgi?action=getConfig&name={name}"
    r = requests.get(url, auth=HTTPDigestAuth(DVR_USER, DVR_PASS))
    return r.text

def detectar_modo():
    config = get_config("MotionDetect[0]")

    linhas = config.split("\r\n")

    enable_line = next(
        (l for l in linhas if l.startswith("table.MotionDetect[0].Enable=")),
        None
    )

    if enable_line and "false" in enable_line:
        return "desativado"

    # Detecta madrugada pela TimeSection
    if "22:00:00" in config and "06:30:00" in config:
        return "madrugada"

    return "24h"


# ================================
# ROTAS
# ================================

@app.route("/")
def index():
    modo = detectar_modo()
    return render_template("index.html", modo=modo)

@app.route("/desativar")
def desativar():
    desativar_total()
    return redirect(url_for("index"))

@app.route("/madrugada")
def madrugada():
    aplicar_madrugada()
    return redirect(url_for("index"))

@app.route("/ativar24h")
def ativar24h():
    aplicar_24h()
    return redirect(url_for("index"))

@app.route("/health")
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False)