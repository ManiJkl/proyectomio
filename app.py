import os
from flask import Flask, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
# Permite que cualquier navegador consulte la API (Fundamental para la web)
CORS(app)

# Cabeceras para simular que somos el navegador oficial y no ser bloqueados por SIUR
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://servicios.siur.com.co/buscarutas/'
}

# ==========================================
# ENDPOINT 1: OBTENER BUSES EN MOVIMIENTO
# ==========================================
@app.route('/api/buses/<ruta>')
def obtener_buses(ruta):
    ruta_clean = ruta.upper()
    url = "https://servicios.siur.com.co/buscarutas/api/buses.php"
    
    try:
        response = requests.get(url, params={'linea': ruta_clean}, headers=HEADERS, timeout=8)
        
        if response.status_code == 200:
            raw_buses = response.json()
            buses_procesados = []

            if isinstance(raw_buses, list):
                for bus in raw_buses:
                    lat_val = float(bus.get('latitud', 0))
                    lng_val = float(bus.get('longitud', 0))

                    if lat_val != 0 and lng_val != 0:
                        buses_procesados.append({
                            "id": bus.get('numeroBus', 'MIO'),
                            "lat": lat_val,
                            "lng": lng_val,
                            "origen": bus.get('paradaInicial', 'Desconocido'),
                            "destino": bus.get('paradaFinal', 'Desconocido'),
                            "tarea": bus.get('tarea', 'N/A'),
                            "viaje": bus.get('viaje', 'N/A'),
                            "nombreLinea": bus.get('nombreLinea', ruta_clean)
                        })

            return jsonify({
                "status": "ok",
                "ruta": ruta_clean,
                "buses": buses_procesados
            })
        
        return jsonify({"status": "error", "message": f"HTTP {response.status_code}"}), response.status_code

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# ENDPOINT 2: OBTENER TRAZADO DEL RECORRIDO
# ==========================================
@app.route('/api/recorrido/<ruta>')
def obtener_recorrido(ruta):
    ruta_clean = ruta.upper()
    url = "https://servicios.siur.com.co/buscarutas/api/recorrido.php"
    
    try:
        response = requests.get(url, params={'linea': ruta_clean}, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            return jsonify({
                "status": "ok",
                "ruta": ruta_clean,
                "puntos": response.json()
            })
        return jsonify({"status": "error", "message": f"HTTP {response.status_code}"}), response.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# ENDPOINT 3: OBTENER PARADAS / ESTACIONES
# ==========================================
@app.route('/api/paradas/<ruta>')
def obtener_paradas(ruta):
    ruta_clean = ruta.upper()
    url = "https://servicios.siur.com.co/buscarutas/api/paradas.php"
    
    try:
        response = requests.get(url, params={'linea': ruta_clean}, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            raw_paradas = response.json()
            paradas_procesadas = []

            if isinstance(raw_paradas, list):
                for parada in raw_paradas:
                    paradas_procesadas.append({
                        "id": parada.get("id"),
                        "lat": float(parada.get("latitud", 0)),
                        "lng": float(parada.get("longitud", 0)),
                        "nombre": parada.get("nombre", "Parada sin nombre")
                    })

            return jsonify({
                "status": "ok",
                "ruta": ruta_clean,
                "paradas": paradas_procesadas
            })
        return jsonify({"status": "error", "message": f"HTTP {response.status_code}"}), response.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# ENDPOINT 4: TIEMPO DE LLEGADA DE BUSES
# ==========================================
@app.route('/api/llegadas/<id_parada>')
def obtener_llegadas(id_parada):
    url = "https://servicios.siur.com.co/buscarutas/api/buses_proximos_a_llegar.php"
    
    try:
        # El parámetro exacto que descubriste: 'parada'
        response = requests.get(url, params={'parada': id_parada}, headers=HEADERS, timeout=8)
        
        if response.status_code == 200:
            return jsonify({
                "status": "ok",
                "parada_id": id_parada,
                "datos": response.json()
            })
            
        return jsonify({"status": "error", "message": f"HTTP {response.status_code}"}), response.status_code

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==========================================
# INICIO DEL SERVIDOR
# ==========================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)