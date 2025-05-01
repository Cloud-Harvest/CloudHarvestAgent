# CHANGELOG

## 0.1.0
- Refactor of the startup routine to be compatible with `gunicorn`
- Plugins are now handled by the CloudHarvestCorePluginManager

## 0.0.2
- Changes supporting CloudHarvestCoreTasks 0.6.3
- The `available_templates` information is now included in the heartbeat
- Added `agent/list_plugins` and `agent/install_plugins` endpoints
- Replaced `pstar` with `accounts` key in heartbeat
- Added `harvest.templates` report
- Updated some templates

## 0.0.1
- Initial implementation
