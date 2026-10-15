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

# Tabla de cabeceras/destinos oficiales para tus rutas frecuentes
CABECERAS_RUTAS = {
    "T12": {
        1: {"origen": "Terminal Menga C2", "destino": "Universidades B1"},
        2: {"origen": "Universidades B1", "destino": "Terminal Menga C2"}
    },
    "P40B": {
        1: {"origen": "Terminal Andrés Sanín", "destino": "Sena / Centro / Cañaveralejo"},
        2: {"origen": "Cañaveralejo / Centro", "destino": "Terminal Andrés Sanín"}
    },
    "A11": {
        1: {"origen": "Estación Universidades", "destino": "Univ. Javeriana / Icesi"},
        2: {"origen": "Univ. Icesi / Javeriana", "destino": "Estación Universidades"}
    },
    "A14A": {
        1: {"origen": "Estación Universidades", "destino": "Univ. del Valle (San Fernando/Meléndez)"},
        2: {"origen": "Univ. del Valle", "destino": "Estación Universidades"}
    }
}

@app.route('/api/buses/<ruta>')
def obtener_buses(ruta):
    ruta_clean = ruta.upper()
    url = "https://servicios.siur.com.co/buscarutas/api/buses.php"
    
    try:
        response = requests.get(
            url,
            params={'linea': ruta_clean},
            headers=HEADERS,
            timeout=8
        )
        
        if response.status_code == 200:
            raw_buses = response.json()
            buses_procesados = []

            if isinstance(raw_buses, list):
                for bus in raw_buses:
                    lat_val = float(bus.get('latitud') or bus.get('lat') or 0)
                    lng_val = float(bus.get('longitud') or bus.get('lng') or bus.get('lon') or 0)

                    # 1. Intentar obtener origen/destino directos si la API de SIUR los trae
                    origen = bus.get('origen') or bus.get('paradaOrigen') or bus.get('cabeceraOrigen')
                    destino = bus.get('destino') or bus.get('paradaDestino') or bus.get('cabeceraDestino')

                    # 2. Si SIUR no trae origen/destino explícitos, usar el sentido mapeado
                    if not origen or not destino:
                        sentido_raw = str(bus.get('sentido') or bus.get('orientacion') or '1')
                        
                        # Determinar si es sentido 1 (Sur/Ida) o 2 (Norte/Vuelta)
                        sentido_num = 1
                        if sentido_raw in ['2', '2.0', 'N', 'NORTE', 'V']:
                            sentido_num = 2
                        elif lat_val > 0 and lat_val > 3.42:  # Apoyo por posición geográfica en Cali
                            sentido_num = 1  # Si está muy al norte, baja hacia el sur

                        cabecera_info = CABECERAS_RUTAS.get(ruta_clean, {}).get(
                            sentido_num, 
                            {"origen": "Cabecera A", "destino": "Cabecera B"}
                        )
                        
                        origen = origen or cabecera_info["origen"]
                        destino = destino or cabecera_info["destino"]

                    buses_procesados.append({
                        "id": str(bus.get('idVehiculo') or bus.get('bus') or bus.get('codigo') or 'MIO'),
                        "lat": lat_val,
                        "lng": lng_val,
                        "origen": origen,
                        "destino": destino
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