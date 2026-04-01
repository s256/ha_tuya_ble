"""Dump all Tuya cloud device info for debugging MAC/UUID matching.

Tries all auth type / app type combinations, same as HA's config flow
(_try_login), and aggregates devices across all successful logins.
"""

import json
import os
import sys

from dotenv import load_dotenv
from tuya_iot import TuyaOpenAPI, AuthType

load_dotenv()

ENDPOINT_MAP = {
    "1": "https://openapi.tuyaus.com",
    "86": "https://openapi.tuyacn.com",
    "49": "https://openapi.tuyaeu.com",
    "91": "https://openapi.tuyain.com",
}

ACCESS_ID = os.getenv("TUYA_ACCESS_ID")
ACCESS_SECRET = os.getenv("TUYA_ACCESS_SECRET")
USERNAME = os.getenv("TUYA_USERNAME")
PASSWORD = os.getenv("TUYA_PASSWORD")
COUNTRY_CODE = os.getenv("TUYA_COUNTRY_CODE", "49")

ENDPOINT = ENDPOINT_MAP.get(COUNTRY_CODE, "https://openapi.tuyaeu.com")

# Same order as _try_login in config_flow.py
AUTH_ATTEMPTS = [
    (AuthType.SMART_HOME, "tuyaSmart"),
    (AuthType.SMART_HOME, "smartlife"),
    (AuthType.CUSTOM, ""),
]


def fetch_devices(api):
    """Fetch all devices and their details for a given authenticated API."""
    devices_resp = api.get(f"/v1.0/users/{api.token_info.uid}/devices")
    if not devices_resp.get("result"):
        return []
    return devices_resp["result"]


def print_device(device, api):
    """Print device details including factory info and specifications."""
    device_id = device.get("id")
    print("=" * 60)
    print(f"Device: {device.get('name')}")
    print(f"  device_id:    {device_id}")
    print(f"  uuid:         {device.get('uuid')}")
    print(f"  category:     {device.get('category')}")
    print(f"  product_id:   {device.get('product_id')}")
    print(f"  product_name: {device.get('product_name')}")
    print(f"  model:        {device.get('model')}")
    print(f"  local_key:    {device.get('local_key', '')[:4]}****")
    print(f"  online:       {device.get('online')}")

    # Factory info (contains MAC)
    fi_resp = api.get(
        f"/v1.0/iot-03/devices/factory-infos?device_ids={device_id}"
    )
    fi_result = fi_resp.get("result", [])
    if fi_result:
        fi = fi_result[0]
        mac = fi.get("mac", "")
        formatted_mac = (
            ":".join(mac[i : i + 2] for i in range(0, len(mac), 2)).upper()
            if mac
            else "N/A"
        )
        print(f"  factory_mac:  {formatted_mac}")
        print(f"  factory_info_raw: {json.dumps(fi)}")
    else:
        print(f"  factory_mac:  N/A (no factory info)")

    # Device specification (functions + status)
    spec_resp = api.get(f"/v1.1/devices/{device_id}/specifications")
    spec_result = spec_resp.get("result", {})
    if spec_result:
        functions = spec_result.get("functions", [])
        status = spec_result.get("status", [])
        print(f"  functions ({len(functions)}):")
        for f in functions:
            print(
                f"    dp_id={f.get('dp_id')} code={f.get('code')} "
                f"type={f.get('type')} values={f.get('values')}"
            )
        print(f"  status_range ({len(status)}):")
        for s in status:
            print(
                f"    dp_id={s.get('dp_id')} code={s.get('code')} "
                f"type={s.get('type')} values={s.get('values')}"
            )
    else:
        print(f"  specifications: N/A")

    print()


def main():
    seen_device_ids = set()

    for auth_type, app_type in AUTH_ATTEMPTS:
        label = f"{auth_type.name}/{app_type or 'none'}"
        api = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_SECRET, auth_type)
        api.set_dev_channel("hass")
        resp = api.connect(USERNAME, PASSWORD, COUNTRY_CODE, app_type)

        if not resp.get("success"):
            print(f"[{label}] Login failed: {resp.get('msg', 'unknown error')}")
            continue

        print(f"[{label}] Login successful.")

        devices = fetch_devices(api)
        new_devices = [d for d in devices if d.get("id") not in seen_device_ids]
        print(f"[{label}] Found {len(devices)} devices ({len(new_devices)} new).\n")

        for device in new_devices:
            seen_device_ids.add(device.get("id"))
            print_device(device, api)

    if not seen_device_ids:
        print("No devices found across any auth method.")
        sys.exit(1)

    print(f"\nTotal unique devices: {len(seen_device_ids)}")


if __name__ == "__main__":
    main()
