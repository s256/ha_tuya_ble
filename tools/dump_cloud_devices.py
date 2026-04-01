"""Dump all Tuya cloud device info for debugging MAC/UUID matching."""

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
APP_TYPE = os.getenv("TUYA_APP_TYPE", "smartlife")

ENDPOINT = ENDPOINT_MAP.get(COUNTRY_CODE, "https://openapi.tuyaeu.com")


def main():
    # Try SMART_HOME first, fall back to CUSTOM
    for auth_type, app_type in [
        (AuthType.SMART_HOME, APP_TYPE),
        (AuthType.CUSTOM, ""),
    ]:
        api = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_SECRET, auth_type)
        api.set_dev_channel("hass")
        resp = api.connect(USERNAME, PASSWORD, COUNTRY_CODE, app_type)
        if resp.get("success"):
            break

    if not resp.get("success"):
        print(f"Login failed: {json.dumps(resp, indent=2)}")
        sys.exit(1)

    print("Login successful.\n")

    # Fetch all devices
    devices_resp = api.get(f"/v1.0/users/{api.token_info.uid}/devices")
    if not devices_resp.get("result"):
        print(f"No devices found: {json.dumps(devices_resp, indent=2)}")
        sys.exit(1)

    devices = devices_resp["result"]
    print(f"Found {len(devices)} devices.\n")

    for device in devices:
        device_id = device.get("id")
        print("=" * 60)
        print(f"Device: {device.get('name')}")
        print(f"  device_id:   {device_id}")
        print(f"  uuid:        {device.get('uuid')}")
        print(f"  category:    {device.get('category')}")
        print(f"  product_id:  {device.get('product_id')}")
        print(f"  product_name:{device.get('product_name')}")
        print(f"  model:       {device.get('model')}")
        print(f"  local_key:   {device.get('local_key', '')[:4]}****")
        print(f"  online:      {device.get('online')}")

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
            print(f"  factory_mac: {formatted_mac}")
            print(f"  factory_info_raw: {json.dumps(fi)}")
        else:
            print(f"  factory_mac: N/A (no factory info)")

        # Device specification (functions + status)
        spec_resp = api.get(f"/v1.1/devices/{device_id}/specifications")
        spec_result = spec_resp.get("result", {})
        if spec_result:
            functions = spec_result.get("functions", [])
            status = spec_result.get("status", [])
            print(f"  functions ({len(functions)}):")
            for f in functions:
                print(f"    dp_id={f.get('dp_id')} code={f.get('code')} type={f.get('type')} values={f.get('values')}")
            print(f"  status_range ({len(status)}):")
            for s in status:
                print(f"    dp_id={s.get('dp_id')} code={s.get('code')} type={s.get('type')} values={s.get('values')}")
        else:
            print(f"  specifications: N/A")

        print()


if __name__ == "__main__":
    main()
