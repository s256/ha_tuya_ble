# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant custom integration for Tuya BLE (Bluetooth Low Energy) devices. Distributed via HACS. Devices communicate locally over BLE but require Tuya IoT cloud credentials (device ID + encryption key) for initial pairing. The integration is a community fork amalgamation — treat as unstable quality.

## Development

This is a Home Assistant custom component — there is no build step, test suite, or linter configured in the repo. Code style uses Black formatting (see recent commit `193f7a8`).

```bash
# Format code
black custom_components/tuya_ble/

# Install in HA for testing: copy or symlink custom_components/tuya_ble/ into your HA config/custom_components/
# Or add your fork as a custom HACS repository
```

Dependencies (from `manifest.json`): `tuya-iot-py-sdk==0.6.6`, `pycountry>23.0.0`, plus HA core bluetooth stack (`bleak`, `bleak_retry_connector`, `home_assistant_bluetooth`).

## Architecture

### Two-layer structure

- **`custom_components/tuya_ble/`** — HA integration layer (config flow, entity platforms, cloud API)
- **`custom_components/tuya_ble/tuya_ble/`** — Inner BLE protocol library (device communication, encryption, GATT operations). This is a vendored/embedded library, not an installable package.

### Key data flow

1. **Discovery**: HA Bluetooth stack discovers devices advertising on service UUID `0000a201-...`
2. **Credentials**: `cloud.py:HASSTuyaBLEDeviceManager` fetches device credentials from Tuya IoT cloud API, caching them keyed by factory MAC address
3. **Connection**: `tuya_ble/tuya_ble.py:TuyaBLEDevice` handles BLE GATT connection, AES encryption, and datapoint read/write
4. **Coordination**: `devices.py:TuyaBLECoordinator` bridges BLE device updates to HA's `DataUpdateCoordinator` pattern
5. **Entities**: Platform files (`sensor.py`, `switch.py`, `light.py`, etc.) map Tuya datapoints (DPIDs) to HA entities

### Device registration pattern

Devices are registered in `devices.py:devices_database` — a dict keyed by Tuya **category ID** (e.g., `"szjqr"` for fingerbots, `"ms"` for locks), containing `TuyaBLECategoryInfo` with product-specific `TuyaBLEProductInfo` entries keyed by **product ID**.

### Two approaches for entity mapping

1. **Legacy DPID-based** (sensor.py, switch.py, number.py, select.py, binary_sensor.py): Entity mappings are hardcoded per-category using numeric DPID mappings (e.g., `TuyaBLESensorMapping(dp_id=1, ...)`). Each category has a dict of `dp_id → description` mappings.

2. **Cloud-driven DPCode-based** (light.py, climate.py, cover.py, lock.py): Entities use `DPCode` enums and resolve DPIDs at runtime via `find_dpcode()`/`find_dpid()` from the device's cloud-fetched specification. This is the newer pattern — the `TuyaBLEEntity` base class in `devices.py` supports both via `send_dp_value()` and `_send_command()`.

### Adding a new device

1. Add a `TuyaBLEProductInfo` entry in `devices.py:devices_database` under the correct category
2. If the category already has entity mappings in the platform files, the device may work automatically
3. If new DPIDs are needed, add mappings in the relevant platform file's category mapping dict
4. See `CONTIBUTING.md` for the workflow using Tuya IoT Platform DPID data

### Key types

- `DPCode` (`const.py`): String enum of Tuya standard data point codes (e.g., `SWITCH`, `TEMP_CURRENT`)
- `DPType` (`const.py`): Data point value types (`Boolean`, `Enum`, `Integer`, `String`, `Json`, `Raw`)
- `TuyaBLEDataPointType` (`tuya_ble/const.py`): BLE-level data point types (`DT_BOOL`, `DT_VALUE`, `DT_STRING`, `DT_ENUM`, `DT_RAW`)
- `TuyaBLEDeviceCredentials` (`tuya_ble/manager.py`): Cloud-fetched device identity (uuid, local_key, device_id, category, product_id, functions, status_range)

### Cloud credential cache

`cloud.py` maintains a module-level `_cache` dict (`TuyaCloudCacheItem`) that maps login credentials to device MAC→credentials. Credentials are looked up by BLE MAC address. Known issue: some devices (e.g., SRB-PM01) have BLE MACs that differ from their cloud factory MACs, causing lookup failures.
