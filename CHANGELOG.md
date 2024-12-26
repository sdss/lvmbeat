# Changelog

## Next version

### ✨ Improved

* Ensure that the monitor tool URL includes the `/heartbeat` route.


## 0.1.1 - December 26, 2024

### ✨ Improved

* Add `timeout` and `outside.interval` configuration options.
* Add documentation on how the product works and deployment instructions.
* Added a `.dockerignore` file.
* Return the `last_seen` value in the monitoring app as an ISO string.

### 🏷️ Changed

* Flatten the monitor app API routes. Renamed `/email/test` to `/email-test`.

### 🔧 Fix

* Fix the `pip` name used to define `__version__`.


## 0.1.0 - December 25, 2024

### 🚀 New

* Initial version with heartbeat middleware and external monitoring service.
