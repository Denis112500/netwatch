# NetWatch
Remote system monitor — Rețele de Calculatoare project.

## Architecture
- **Agent** — collects CPU/RAM/disk/network metrics and streams them to the server
- **Server** — receives metrics from multiple agents, stores state, triggers alerts
- **Dashboard** — live web UI showing all connected agents

## Protocol
Custom TCP application-layer protocol

