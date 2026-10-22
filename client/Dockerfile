# Multi-stage Next.js standalone image (~140-170 MB).
#
# The official node:20-alpine image is ~129 MB uncompressed because it ships
# npm, corepack and a Node binary with debug symbols. A standalone Next server
# only needs the Node binary, so the final stage starts from plain Alpine and
# copies exactly that.
FROM node:20.20.2-alpine3.23 AS deps
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json ./
# The repo has no package-lock.json yet, so npm ci cannot be used.
RUN npm install --no-audit --no-fund

FROM node:20.20.2-alpine3.23 AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY package.json next.config.js tsconfig.json ./
COPY src ./src
RUN npm run build \
    && find /app/.next/standalone /app/.next/static -type f \( -name '*.map' -o -name '*.d.ts' \) -delete \
    && if [ -d /app/.next/standalone/node_modules ]; then \
         find /app/.next/standalone/node_modules -type f -name '*.md' -delete; \
       fi

FROM alpine:3.23 AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# Node's musl binary needs libstdc++/libgcc; ca-certificates covers outbound TLS.
RUN apk add --no-cache libstdc++ libgcc ca-certificates \
    && addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 --ingroup nodejs nextjs \
    && mkdir -p /app/.next/cache \
    && chown -R nextjs:nodejs /app

COPY --from=builder /usr/local/bin/node /usr/local/bin/node

# Standalone output contains server.js plus only the traced runtime modules.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD wget -qO- http://127.0.0.1:3000/health || exit 1

CMD ["node", "server.js"]
