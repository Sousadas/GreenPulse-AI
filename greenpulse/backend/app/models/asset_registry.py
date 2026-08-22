"""Asset registry — defines the renewable energy park in Kutch & Banaskantha."""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.schemas import Asset, AssetStatus, AssetType

# ---------------------------------------------------------------------------
# Kutch Solar Farm assets
# ---------------------------------------------------------------------------
_KUTCH_SOLAR_PANELS = [
    Asset(
        asset_id=f"SOL-PNL-{i:03d}",
        asset_type=AssetType.SOLAR_PANEL,
        location="Kutch, Gujarat",
        capacity_kw=500.0,
        manufacturer="Waaree Energies",
        model="WS-500M",
        installation_date=datetime(2022, 3, 15, tzinfo=timezone.utc),
        status=AssetStatus.ONLINE,
        latitude=23.733,
        longitude=69.867,
    )
    for i in range(1, 11)  # 10 panels × 500 kW = 5 MW solar
]

_KUTCH_INVERTERS = [
    Asset(
        asset_id=f"SOL-INV-{i:03d}",
        asset_type=AssetType.SOLAR_INVERTER,
        location="Kutch, Gujarat",
        capacity_kw=500.0,
        manufacturer="ABB",
        model="TRIO-50.0-TL-OUTD",
        installation_date=datetime(2022, 3, 15, tzinfo=timezone.utc),
        status=AssetStatus.ONLINE,
        latitude=23.733,
        longitude=69.867,
    )
    for i in range(1, 6)  # 5 inverters
]

# Notorious demonstration inverter — starts healthy, can degrade
_SOL_INV_042 = Asset(
    asset_id="SOL-INV-042",
    asset_type=AssetType.SOLAR_INVERTER,
    location="Kutch, Gujarat",
    capacity_kw=500.0,
    manufacturer="ABB",
    model="TRIO-50.0-TL-OUTD",
    installation_date=datetime(2021, 6, 1, tzinfo=timezone.utc),
    status=AssetStatus.ONLINE,
    latitude=23.735,
    longitude=69.869,
)

# ---------------------------------------------------------------------------
# Kutch Wind Farm assets
# ---------------------------------------------------------------------------
_KUTCH_WIND_TURBINES = [
    Asset(
        asset_id=f"WT-{i:03d}",
        asset_type=AssetType.WIND_TURBINE,
        location="Kutch, Gujarat",
        capacity_kw=2000.0,
        manufacturer="Suzlon Energy",
        model="S111-2.1 MW",
        installation_date=datetime(2021, 11, 20, tzinfo=timezone.utc),
        status=AssetStatus.ONLINE,
        latitude=23.75 + i * 0.005,
        longitude=69.85 + i * 0.003,
    )
    for i in range(1, 9)  # 8 turbines × 2 MW = 16 MW wind
]

# Demonstration turbine — can overheat
_WT_017 = Asset(
    asset_id="WT-017",
    asset_type=AssetType.WIND_TURBINE,
    location="Kutch, Gujarat",
    capacity_kw=2000.0,
    manufacturer="Suzlon Energy",
    model="S111-2.1 MW",
    installation_date=datetime(2020, 8, 5, tzinfo=timezone.utc),
    status=AssetStatus.ONLINE,
    latitude=23.780,
    longitude=69.900,
)

# ---------------------------------------------------------------------------
# Banaskantha Solar Farm
# ---------------------------------------------------------------------------
_BANAS_SOLAR_PANELS = [
    Asset(
        asset_id=f"BAN-PNL-{i:03d}",
        asset_type=AssetType.SOLAR_PANEL,
        location="Banaskantha, Gujarat",
        capacity_kw=400.0,
        manufacturer="Adani Solar",
        model="ASPM-400M",
        installation_date=datetime(2023, 1, 10, tzinfo=timezone.utc),
        status=AssetStatus.ONLINE,
        latitude=24.17,
        longitude=72.43,
    )
    for i in range(1, 9)  # 8 panels × 400 kW = 3.2 MW
]

_BANAS_INVERTERS = [
    Asset(
        asset_id=f"BAN-INV-{i:03d}",
        asset_type=AssetType.SOLAR_INVERTER,
        location="Banaskantha, Gujarat",
        capacity_kw=800.0,
        manufacturer="SMA Solar",
        model="SUNNY CENTRAL 800CP-JP",
        installation_date=datetime(2023, 1, 10, tzinfo=timezone.utc),
        status=AssetStatus.ONLINE,
        latitude=24.17,
        longitude=72.43,
    )
    for i in range(1, 5)  # 4 inverters
]

# ---------------------------------------------------------------------------
# Transformers & Grid Interface
# ---------------------------------------------------------------------------
_TRANSFORMERS = [
    Asset(
        asset_id="TRF-KUT-01",
        asset_type=AssetType.TRANSFORMER,
        location="Kutch, Gujarat",
        capacity_kw=25000.0,
        manufacturer="BHEL",
        model="25MVA-132/33kV",
        installation_date=datetime(2021, 6, 1, tzinfo=timezone.utc),
        status=AssetStatus.ONLINE,
    ),
    Asset(
        asset_id="TRF-BAN-01",
        asset_type=AssetType.TRANSFORMER,
        location="Banaskantha, Gujarat",
        capacity_kw=10000.0,
        manufacturer="BHEL",
        model="10MVA-132/33kV",
        installation_date=datetime(2023, 1, 10, tzinfo=timezone.utc),
        status=AssetStatus.ONLINE,
    ),
]

_GRID_INTERFACES = [
    Asset(
        asset_id="GRD-KUT-01",
        asset_type=AssetType.GRID_INTERFACE,
        location="Kutch, Gujarat",
        capacity_kw=25000.0,
        manufacturer="Siemens",
        model="SIPROTEC-5",
        installation_date=datetime(2021, 6, 1, tzinfo=timezone.utc),
        status=AssetStatus.ONLINE,
    ),
]

# ---------------------------------------------------------------------------
# Aggregated registry
# ---------------------------------------------------------------------------
ALL_ASSETS: list[Asset] = (
    _KUTCH_SOLAR_PANELS
    + _KUTCH_INVERTERS
    + [_SOL_INV_042]
    + _KUTCH_WIND_TURBINES
    + [_WT_017]
    + _BANAS_SOLAR_PANELS
    + _BANAS_INVERTERS
    + _TRANSFORMERS
    + _GRID_INTERFACES
)

ASSET_MAP: dict[str, Asset] = {a.asset_id: a for a in ALL_ASSETS}


def get_asset(asset_id: str) -> Asset | None:
    return ASSET_MAP.get(asset_id)


def list_assets(asset_type: AssetType | None = None) -> list[Asset]:
    if asset_type is None:
        return list(ALL_ASSETS)
    return [a for a in ALL_ASSETS if a.asset_type == asset_type]
