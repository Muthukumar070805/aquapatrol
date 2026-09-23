"""Fixed demo scenario: slick origin plus four simulated-AIS vessels.

All coordinates lie within 50km of ``ORIGIN``; all timestamps are ISO-8601
``Z`` strings. ``MT CORALIS`` carries a 2.1h AIS gap (00:20Z -> 02:30Z on
2020-07-25) to simulate a dark-vessel transit. Source for every track point
is ``simulated_ais`` — deterministic fixture data, never real AIS.
"""

from __future__ import annotations

from typing import Any

ORIGIN: dict[str, Any] = {
    "lat": -20.44,
    "lon": 57.72,
    "detection_time": "2020-07-25T04:35:00Z",
    "slick_area_km2": 3.1,
}

VESSELS: list[dict[str, Any]] = [
    {
        "id": "vessel-coralis",
        "name": "MT CORALIS",
        "mmsi": "636021478",
        "imo": "9351282",
        "flag": "Liberia",
        "vessel_type": "tanker",
        "lat": -20.38,
        "lon": 57.66,
        "speed": 9.2,
        "heading": 135,
        "ais_status": "PARTIAL",
        "dark_vessel": 1,
        "last_seen": "2020-07-25T02:30:00Z",
        "suspicion_level": "high",
        "TRACKS": [
            ("2020-07-24T22:00:00Z", -20.30, 57.58, 9.5, 135),
            ("2020-07-24T23:10:00Z", -20.33, 57.60, 9.4, 135),
            ("2020-07-25T00:20:00Z", -20.36, 57.63, 9.3, 135),
            ("2020-07-25T02:30:00Z", -20.38, 57.66, 9.2, 135),
        ],
    },
    {
        "id": "vessel-pioneer",
        "name": "OCEAN PIONEER",
        "mmsi": "412881000",
        "imo": "9221145",
        "flag": "China",
        "vessel_type": "bulk_carrier",
        "lat": -20.50,
        "lon": 57.78,
        "speed": 11.5,
        "heading": 280,
        "ais_status": "FULL",
        "dark_vessel": 0,
        "last_seen": "2020-07-25T04:00:00Z",
        "suspicion_level": "medium",
        "TRACKS": [
            ("2020-07-25T01:00:00Z", -20.52, 57.84, 11.8, 280),
            ("2020-07-25T02:00:00Z", -20.51, 57.81, 11.6, 280),
            ("2020-07-25T03:00:00Z", -20.505, 57.795, 11.5, 280),
            ("2020-07-25T04:00:00Z", -20.50, 57.78, 11.5, 280),
        ],
    },
    {
        "id": "vessel-seabright",
        "name": "SEABRIGHT",
        "mmsi": "538006123",
        "imo": "9634567",
        "flag": "Marshall Islands",
        "vessel_type": "container",
        "lat": -20.46,
        "lon": 57.70,
        "speed": 8.0,
        "heading": 90,
        "ais_status": "FULL",
        "dark_vessel": 0,
        "last_seen": "2020-07-25T03:30:00Z",
        "suspicion_level": "low",
        "TRACKS": [
            ("2020-07-25T02:00:00Z", -20.46, 57.64, 8.2, 90),
            ("2020-07-25T03:00:00Z", -20.46, 57.67, 8.1, 90),
            ("2020-07-25T03:30:00Z", -20.46, 57.70, 8.0, 90),
        ],
    },
    {
        "id": "vessel-dhow",
        "name": "DHOW",
        "mmsi": "620999012",
        "imo": "0000000",
        "flag": "Mauritius",
        "vessel_type": "fishing",
        "lat": -20.42,
        "lon": 57.74,
        "speed": 5.2,
        "heading": 11,
        "ais_status": "FULL",
        "dark_vessel": 0,
        "last_seen": "2020-07-25T03:30:00Z",
        "suspicion_level": "low",
        "TRACKS": [
            ("2020-07-25T01:30:00Z", -20.40, 57.735, 5.5, 11),
            ("2020-07-25T02:30:00Z", -20.41, 57.738, 5.3, 11),
            ("2020-07-25T03:30:00Z", -20.42, 57.74, 5.2, 11),
        ],
    },
]

SCENARIO: dict[str, Any] = {
    "name": "mauritius-2020-07-25-demo",
    "description": "Deterministic demo: 2020-07-25 slick with four simulated vessels.",
    "source": "simulated_ais",
    "origin": ORIGIN,
    "vessels": VESSELS,
}

__all__ = ["ORIGIN", "SCENARIO", "VESSELS"]
