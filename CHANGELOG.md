# Changelog

## Next version

### 🚀 New

* Do not emit heartbeat to ECP if the network (LCO or internet) is down.


## 0.1.2 - December 27, 2024

### ✨ Improved

* Ensure that the monitor tool URL includes the `/heartbeat` route.
* Report ISO strings with a precision of seconds.
* Report when the last connection with the LCO server was made in the alert email.

### 🔧 Fix

* Update when the last heartbeat was sent to the ECP.
* Fixed double `ENV` statement in dockerfile.


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
