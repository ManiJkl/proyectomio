import os
from flask import Flask, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://servicios.siur.com.co/buscarutas/'
}

@app.route('/api/buses/<ruta>')
def obtener_buses(ruta):
    url = "https://servicios.siur.com.co/buscarutas/api/buses.php"
    try:
        response = requests.get(url, params={'linea': ruta.upper()}, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            return jsonify({"status": "ok", "ruta": ruta.upper(), "buses": response.json()})
        return jsonify({"status": "error", "message": f"HTTP {response.status_code}"}), response.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Usamos el puerto que asigna la nube o el 5000 por defecto
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)