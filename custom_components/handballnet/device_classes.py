from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import PERCENTAGE

# Benutzerdefinierte Device Classes für bessere Kategorisierung
DEVICE_CLASS_STATISTICS = "handball_statistics"
DEVICE_CLASS_SCHEDULE = "handball_schedule" 
DEVICE_CLASS_LIVE = "handball_live"
DEVICE_CLASS_TABLE = "handball_table"

# Sensor-Kategorien für Home Assistant
SENSOR_CATEGORIES = {
    "statistics": {
        "name": "Statistiken",
        "icon": "mdi:chart-line",
        "device_class": DEVICE_CLASS_STATISTICS
    },
    "schedule": {
        "name": "Spielplan",
        "icon": "mdi:calendar",
        "device_class": DEVICE_CLASS_SCHEDULE
    },
    "live": {
        "name": "Live",
        "icon": "mdi:television-play",
        "device_class": DEVICE_CLASS_LIVE
    },
    "table": {
        "name": "Tabelle",
        "icon": "mdi:trophy",
        "device_class": DEVICE_CLASS_TABLE
    }
}
