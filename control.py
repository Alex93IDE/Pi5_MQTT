from helpers import run
from config import API


def handle_control(payload):
    a = payload.get("action")
    if   a == "oled_on":         run(f"curl -s -X POST {API}/set-oled-enable -H 'Content-Type: application/json' -d '{{\"enable\": true}}'")
    elif a == "oled_off":        run(f"curl -s -X POST {API}/set-oled-enable -H 'Content-Type: application/json' -d '{{\"enable\": false}}'")
    elif a == "rgb_on":          run(f"curl -s -X POST {API}/set-rgb-enable -H 'Content-Type: application/json' -d '{{\"enable\": true}}'")
    elif a == "rgb_off":         run(f"curl -s -X POST {API}/set-rgb-enable -H 'Content-Type: application/json' -d '{{\"enable\": false}}'")
    elif a == "rgb_color":
        color = payload.get("color", "#ffffff")
        run(f"curl -s -X POST {API}/set-rgb-color -H 'Content-Type: application/json' -d '{{\"color\": \"{color}\"}}'")
    elif a == "rgb_style":
        style = payload.get("style", "breathing")
        run(f"curl -s -X POST {API}/set-rgb-style -H 'Content-Type: application/json' -d '{{\"style\": \"{style}\"}}'")
    elif a == "rgb_brightness":
        value = payload.get("value", 50)
        run(f"curl -s -X POST {API}/set-rgb-brightness -H 'Content-Type: application/json' -d '{{\"brightness\": {value}}}'")
    elif a == "rgb_speed":
        value = payload.get("value", 50)
        run(f"curl -s -X POST {API}/set-rgb-speed -H 'Content-Type: application/json' -d '{{\"speed\": {value}}}'")
    elif a == "fan_mode":
        mode = payload.get("mode", 1)  # 0=Always On, 1=Performance, 2=Cool, 3=Balance, 4=Silent
        run(f"curl -s -X POST {API}/set-fan-mode -H 'Content-Type: application/json' -d '{{\"fan_mode\": {mode}}}'")
