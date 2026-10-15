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
                            # Campos esenciales para que funcione el frontend actual
                            "id": bus.get('numeroBus', 'MIO'),
                            "lat": lat_val,
                            "lng": lng_val,
                            "origen": bus.get('paradaInicial', 'Desconocido'),
                            "destino": bus.get('paradaFinal', 'Desconocido'),
                            
                            # Toda la nueva información extraída directamente de SIUR
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)