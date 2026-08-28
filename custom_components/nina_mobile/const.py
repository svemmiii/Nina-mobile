"""Constants for NINA Mobile."""

from datetime import timedelta

DOMAIN = "nina_mobile"

CONF_TRACKER = "tracker_entity_id"
CONF_MESSAGE_SLOTS = "message_slots"

DEFAULT_MESSAGE_SLOTS = 5
MIN_MESSAGE_SLOTS = 1
MAX_MESSAGE_SLOTS = 20

SCAN_INTERVAL = timedelta(minutes=5)

BKG_WFS_URL = "https://sgx.geodatenzentrum.de/wfs_vg250"
BKG_WFS_TYPENAME = "vg250_krs"
BKG_BBOX_EPSILON = 0.0002

ATTR_WARNING_ID = "warning_id"
ATTR_ID = "id"
ATTR_HEADLINE = "headline"
ATTR_DESCRIPTION = "description"
ATTR_SENDER = "sender"
ATTR_SEVERITY = "severity"
ATTR_RECOMMENDED_ACTIONS = "recommended_actions"
ATTR_AFFECTED_AREAS = "affected_areas"
ATTR_MORE_INFO_URL = "more_info_url"
ATTR_WEB = "web"
ATTR_SENT = "sent"
ATTR_START = "start"
ATTR_EXPIRES = "expires"
ATTR_ARS = "ars"
ATTR_REGION = "region"
ATTR_TRACKER = "tracker_entity_id"
ATTR_GPS_AVAILABLE = "gps_available"
ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"
ATTR_OUTSIDE_GERMANY = "outside_germany"
ATTR_WARNING_COUNT = "warning_count"
