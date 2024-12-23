# lvmbeat

Middleware that monitors various heartbeats from different sources (Overwatcher, `lvmecp`, etc.) and sets the dome heartbeat.

It also emits an external heartbeat every 5 seconds to inform the outside world that the internet connection to LCO is active.
