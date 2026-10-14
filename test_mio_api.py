import json
import time
import requests

# Endpoint actual utilizado por Buscarutas MIO / SIUR.
BASE_URLS = [
    "https://servicios.siur.com.co/buscarutas/api/buses.php"
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://servicios.siur.com.co/buscarutas/'
}

def probar_conexion_ruta(nombre_ruta="T31"):
    """
    Intenta consultar los buses activos en una ruta específica (ej. T31, A11, P21C)
    probando diferentes variaciones de parámetros aceptados por SIUR.
    """
    print("=" * 60)
    print(f"PROBANDO CONEXION EN TIEMPO REAL PARA LA RUTA MIO: {nombre_ruta}")
    print("=" * 60)

    exito = False

    for url in BASE_URLS:
        print(f"\n[+] Probando endpoint: {url}")
        
        try:
            response = requests.get(
                url,
                params={'linea': nombre_ruta},
                headers=HEADERS,
                timeout=10
            )
            print(f"    - GET {response.url} -> Estado HTTP: {response.status_code}")

            if response.status_code == 200 and response.text.strip():
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    print("    - La respuesta no es un JSON válido.")
                    continue

                if data:
                    print("\nRESPUESTA CON DATOS RECIBIDA EXITOSAMENTE")
                    print(f"   Estructura recibida ({len(data)} elementos/objetos):")
                    print(json.dumps(data[:3] if isinstance(data, list) else data, indent=2, ensure_ascii=False))
                    exito = True
                    return data
        except requests.exceptions.RequestException as e:
            print(f"    - Error de conexión: {e}")

    if not exito:
        print("\nNo se obtuvo una respuesta JSON valida desde los endpoints por defecto.")
        print("Nota: SIUR puede requerir token de sesion o captcha temporal en su web.")

    return None

if __name__ == "__main__":
    print("Iniciando prueba de captura de datos MIO Cali...")
    probar_conexion_ruta("T31")
