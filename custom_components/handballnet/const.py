DOMAIN = "handballnet"
CONF_TEAM_ID = "team_id"
CONF_LEAGUE_ID = "league_id"
CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_UPDATE_INTERVAL = 3600  
CONF_UPDATE_INTERVAL_LIVE = "update_interval_live"
DEFAULT_UPDATE_INTERVAL_LIVE = 15

# Game duration and health check constants
GAME_DURATION_HOURS = 2
HEALTH_CHECK_STALE_HOURS = 2
LIVE_GAME_CHECK_INTERVAL = 60

# API endpoints
HANDBALL_NET_BASE_URL = "https://www.handball.net/a/sportdata/1"
HANDBALL_NET_LOGO_PREFIX = "handball-net:"
HANDBALL_NET_WEB_URL = "https://www.handball.net/"

# Date format constants
DATE_FORMAT_UTC = "%Y-%m-%d %H:%M:%S UTC"
DATE_FORMAT_LOCAL = "%Y-%m-%d %H:%M:%S"

# Health status constants
HEALTH_STATUS_HEALTHY = "healthy"
HEALTH_STATUS_DEGRADED = "degraded"
HEALTH_STATUS_UNHEALTHY = "unhealthy"
HEALTH_STATUS_STALE = "stale"
HEALTH_STATUS_ERROR = "error"
HEALTH_STATUS_UNKNOWN = "unknown"