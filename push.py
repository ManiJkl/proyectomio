"""Avisos push: avisan cuando un bus de una línea está cerca de una parada.

Flujo:
  1. El navegador pide la clave pública VAPID (GET /api/push/key).
  2. Se suscribe y registra avisos (POST /api/push/alerts).
  3. Un hilo en segundo plano consulta las llegadas de las paradas con avisos
     activos y, cuando un bus de la línea está a <= `minutes` minutos, envía el
     push y borra el aviso (cada aviso se dispara una sola vez).

Variables de entorno:
  VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY  claves VAPID (ver generate_vapid_keys.py)
  VAPID_SUBJECT                          "mailto:tu@correo.com"
  PUSH_DATA_FILE                         archivo JSON donde se guardan los avisos
  PUSH_POLL_SECONDS                      cada cuánto se revisan las llegadas (30)
  DISABLE_PUSH_WORKER                    "1" para no iniciar el hilo (pruebas)
"""
import json
import os
import re
import threading
import time
import uuid

from flask import Blueprint, jsonify, request

try:
    from pywebpush import WebPushException, webpush
except ImportError:  # el resto de la API sigue funcionando sin pywebpush
    webpush = None
    WebPushException = Exception

VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_SUBJECT = os.environ.get('VAPID_SUBJECT', 'mailto:admin@example.com')
DATA_FILE = os.environ.get('PUSH_DATA_FILE', '/tmp/mio_push_data.json')
POLL_SECONDS = int(os.environ.get('PUSH_POLL_SECONDS', '30'))

MAX_ALERTS_PER_SUBSCRIPTION = 10
ALERT_TTL_SECONDS = 3 * 60 * 60  # un aviso que no se cumple en 3 h se descarta
MIN_MINUTES, MAX_MINUTES = 1, 15

bp = Blueprint('push', __name__)
_lock = threading.Lock()
# {endpoint: {"subscription": {...}, "alerts": {alert_id: {...}}}}
_store = {}
_fetch_arrivals = None


def push_enabled():
    return bool(webpush and VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)


# --------------------------------------------------------------- persistencia
def _load():
    try:
        with open(DATA_FILE, encoding='utf-8') as handle:
            _store.update(json.load(handle))
    except (OSError, ValueError):
        pass


def _save():
    """Llamar con _lock tomado."""
    try:
        tmp = DATA_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as handle:
            json.dump(_store, handle)
        os.replace(tmp, DATA_FILE)
    except OSError:
        pass


# ------------------------------------------------------------------ utilidades
def parse_minutes(countdown):
    """'5 min' -> 5, 'Llegando' -> 0, cualquier otra cosa -> None."""
    if not isinstance(countdown, str):
        return None
    text = countdown.strip().lower()
    match = re.search(r'\d+', text)
    if match:
        return int(match.group())
    if re.search(r'lleg|ahora|inminente|<', text):
        return 0
    return None


def _valid_subscription(sub):
    return (
        isinstance(sub, dict)
        and isinstance(sub.get('endpoint'), str)
        and sub['endpoint'].startswith('https://')
        and isinstance(sub.get('keys'), dict)
        and sub['keys'].get('p256dh')
        and sub['keys'].get('auth')
    )


def _clean_alert(raw):
    if not isinstance(raw, dict):
        return None
    stop_id = str(raw.get('stopId', '')).strip()
    line = str(raw.get('line', '')).strip().upper()
    try:
        minutes = int(raw.get('minutes', 3))
    except (TypeError, ValueError):
        return None
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,20}', stop_id):
        return None
    if not re.fullmatch(r'[A-Z0-9]{1,8}', line):
        return None
    return {
        'id': str(raw.get('id') or uuid.uuid4().hex)[:40],
        'stopId': stop_id,
        'stopName': str(raw.get('stopName', ''))[:80],
        'line': line,
        'minutes': max(MIN_MINUTES, min(MAX_MINUTES, minutes)),
        'created': time.time(),
    }


# -------------------------------------------------------------------- endpoints
@bp.route('/api/push/key')
def push_key():
    if not push_enabled():
        return jsonify({'status': 'disabled'}), 503
    return jsonify({'status': 'ok', 'publicKey': VAPID_PUBLIC_KEY})


@bp.route('/api/push/alerts', methods=['POST'])
def add_alert():
    if not push_enabled():
        return jsonify({'status': 'disabled'}), 503
    body = request.get_json(silent=True) or {}
    subscription = body.get('subscription')
    alert = _clean_alert(body.get('alert'))
    if not _valid_subscription(subscription) or not alert:
        return jsonify({'status': 'error', 'message': 'datos inválidos'}), 400

    with _lock:
        entry = _store.setdefault(subscription['endpoint'], {'subscription': subscription, 'alerts': {}})
        entry['subscription'] = subscription
        if alert['id'] not in entry['alerts'] and len(entry['alerts']) >= MAX_ALERTS_PER_SUBSCRIPTION:
            return jsonify({'status': 'error', 'message': 'límite de avisos alcanzado'}), 429
        entry['alerts'][alert['id']] = alert
        _save()
    return jsonify({'status': 'ok', 'alert': alert})


@bp.route('/api/push/alerts/list', methods=['POST'])
def list_alerts():
    """Avisos activos de una suscripción (POST para no poner el endpoint en la URL)."""
    endpoint = (request.get_json(silent=True) or {}).get('endpoint')
    with _lock:
        entry = _store.get(endpoint)
        alerts = list(entry['alerts'].values()) if entry else []
    return jsonify({'status': 'ok', 'alerts': alerts})


@bp.route('/api/push/alerts/delete', methods=['POST'])
def delete_alert():
    body = request.get_json(silent=True) or {}
    endpoint, alert_id = body.get('endpoint'), body.get('id')
    with _lock:
        entry = _store.get(endpoint)
        if entry:
            if alert_id:
                entry['alerts'].pop(alert_id, None)
            else:  # sin id: se quita la suscripción completa
                _store.pop(endpoint, None)
            _save()
    return jsonify({'status': 'ok'})


# ------------------------------------------------------------------- el vigía
def _notify(subscription, alert, minutes, destination):
    where = alert['stopName'] or f"parada {alert['stopId']}"
    when = 'está llegando' if minutes <= 0 else f'llega en {minutes} min'
    payload = {
        'title': f"{alert['line']} {when}",
        'body': f"Hacia {destination} · {where}" if destination else where,
        'tag': alert['id'],
        'alertId': alert['id'],
        'stopId': alert['stopId'],
    }
    webpush(
        subscription_info=subscription,
        data=json.dumps(payload),
        vapid_private_key=VAPID_PRIVATE_KEY,
        vapid_claims={'sub': VAPID_SUBJECT},
        ttl=120,
    )


def check_alerts():
    """Una pasada: revisa las paradas con avisos y envía los pushes que toquen."""
    now = time.time()
    with _lock:
        by_stop = {}
        for endpoint, entry in list(_store.items()):
            for alert_id, alert in list(entry['alerts'].items()):
                if now - alert['created'] > ALERT_TTL_SECONDS:
                    del entry['alerts'][alert_id]
                    continue
                by_stop.setdefault(alert['stopId'], []).append((endpoint, alert))
            if not entry['alerts']:
                del _store[endpoint]
        _save()

    for stop_id, pending in by_stop.items():
        try:
            buses = _fetch_arrivals(stop_id)
        except Exception:
            continue
        for endpoint, alert in pending:
            matches = []
            for bus in buses:
                minutes = parse_minutes(bus.get('cuentaRegresiva'))
                if minutes is not None and str(bus.get('nombreLinea', '')).upper() == alert['line']:
                    matches.append((minutes, bus.get('nombreDestino', '')))
            if not matches:
                continue
            minutes, destination = min(matches)
            if minutes > alert['minutes']:
                continue

            with _lock:
                entry = _store.get(endpoint)
                if not entry or alert['id'] not in entry['alerts']:
                    continue
                subscription = entry['subscription']
            try:
                _notify(subscription, alert, minutes, destination)
            except WebPushException as err:
                status = getattr(getattr(err, 'response', None), 'status_code', None)
                if status in (404, 410):  # suscripción muerta
                    with _lock:
                        _store.pop(endpoint, None)
                        _save()
                continue
            except Exception:
                continue
            with _lock:
                entry = _store.get(endpoint)
                if entry:
                    entry['alerts'].pop(alert['id'], None)
                    if not entry['alerts']:
                        _store.pop(endpoint, None)
                    _save()


def _worker():
    while True:
        try:
            check_alerts()
        except Exception as err:  # el hilo nunca debe morir
            print(f'[push] error: {err}')
        time.sleep(POLL_SECONDS)


def init_push(app, fetch_arrivals):
    """`fetch_arrivals(stop_id)` devuelve la lista de buses de la parada."""
    global _fetch_arrivals
    _fetch_arrivals = fetch_arrivals
    app.register_blueprint(bp)
    _load()
    if push_enabled() and os.environ.get('DISABLE_PUSH_WORKER') != '1':
        threading.Thread(target=_worker, name='push-worker', daemon=True).start()
