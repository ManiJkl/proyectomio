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
        response = requests.get(
            url,
            params={'linea': ruta.upper()},
            headers=HEADERS,
            timeout=8
        )
        
        if response.status_code == 200:
            raw_buses = response.json()
            buses_procesados = []

            if isinstance(raw_buses, list):
                for bus in raw_buses:
                    # Extraer sentido / rumbo original
                    sentido_raw = bus.get('sentido') or bus.get('orientacion') or bus.get('dir')
                    rumbo_raw = bus.get('rumbo') or bus.get('bearing') or bus.get('heading')

                    # Mapeo de orientación legible para Cali (Eje Norte-Sur)
                    sentido_texto = "Desconocido"
                    if sentido_raw in [1, "1", "S", "SUR"]:
                        sentido_texto = "Sentido Sur (ej. hacia Universidades/Capri)"
                    elif sentido_raw in [2, "2", "N", "NORTE"]:
                        sentido_texto = "Sentido Norte (ej. hacia Menga/Paso del Comercio)"
                    elif rumbo_raw is not None:
                        try:
                            rumbo = float(rumbo_raw)
                            # 90° a 270° generalmente apunta hacia el Sur en Cali
                            if 90 <= rumbo <= 270:
                                sentido_texto = "Hacia el Sur"
                            else:
                                sentido_texto = "Hacia el Norte"
                        except ValueError:
                            pass

                    buses_procesados.append({
                        "id": bus.get('idVehiculo') or bus.get('bus') or bus.get('codigo') or 'MIO',
                        "lat": bus.get('latitud') or bus.get('lat'),
                        "lng": bus.get('longitud') or bus.get('lng') or bus.get('lon'),
                        "sentido": sentido_texto,
                        "rumbo": rumbo_raw
                    })

            return jsonify({
                "status": "ok",
                "ruta": ruta.upper(),
                "buses": buses_procesados
            })
        
        return jsonify({"status": "error", "message": f"HTTP {response.status_code}"}), response.status_code

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)