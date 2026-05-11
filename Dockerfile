# syntax=docker/dockerfile:1
# Build a tiny static-site image for Railway using Caddy.
# Railway sets $PORT — Caddyfile binds to it. TLS is terminated at Railway's edge.

FROM caddy:2-alpine

# Site content
COPY . /usr/share/caddy/

# Caddy config (drop after the COPY above so the Caddyfile inside the image
# is the dedicated one, not the literal file checked into /usr/share/caddy/)
COPY Caddyfile /etc/caddy/Caddyfile

# Healthcheck — Railway also uses this
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:${PORT:-8080}/ > /dev/null || exit 1
