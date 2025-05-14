# CHANGELOG

## 0.1.3
- [Platform configuration needs to allow different role names per account](https://github.com/Cloud-Harvest/CloudHarvestAgent/issues/10)

## 0.1.2
- Updated to conform with CloudHarvestCoreTasks 0.6.5

## 0.1.1
- CloudHarvestCoreTasks 0.6.4
- [Part of the Redis Task Standardization Effort](https://github.com/Cloud-Harvest/CloudHarvestAgent/issues/8)
- Improved heartbeat by reducing the size of the upload payload
- Refactored the TaskChainQueue
- Heartbeat will now send all datapoints per cycle to prevent scenarios where some fields are present and others are not
- Fixed some issues where 
  - templates got clobbered (missing `deepycopy`)
  - datetimes where not uniformly TZ aware
  - missing TaskChain classes did not raise useful errors
- Most TaskChain status updates are now handled within the `BaseTaskChain` class
- Updated many templates

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
