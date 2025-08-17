FROM node:20-alpine AS deps

# Set build-time environment variables
# Don't set NODE_ENV to avoid Next.js warnings
ENV NEXT_TELEMETRY_DISABLED=1
ENV PRISMA_ENGINES_CHECKSUM_IGNORE_MISSING=1

# Install dependencies for native modules
RUN apk add --no-cache \
    curl python3 make g++ openssl
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY prisma ./prisma/

# Install ALL dependencies (including devDependencies) for build stage
RUN npm ci --include=dev --ignore-scripts

# Manually install Prisma CLI dependencies to ensure it works
RUN cd node_modules/prisma && npm install --production || true

# Builder stage
FROM node:20-alpine AS builder

# Install OpenSSL for Prisma
RUN apk add --no-cache \
    openssl

# Set build-time environment variables
# Don't set NODE_ENV to avoid Next.js warnings
ENV NEXT_TELEMETRY_DISABLED=1
ENV PRISMA_ENGINES_CHECKSUM_IGNORE_MISSING=1

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Generate Prisma client during build
# Use the installed prisma to generate, avoiding binary download issues
RUN npx prisma generate --schema=./prisma/schema.prisma || \
    (echo "Prisma generation failed, trying alternative approach..." && \
     node node_modules/prisma/build/index.js generate --schema=./prisma/schema.prisma)

# Build Next.js application
ENV NEXT_TELEMETRY_DISABLED 1
# Set NODE_ENV for build to match runtime expectations
ARG NODE_ENV=development
ENV NODE_ENV=${NODE_ENV}
RUN npm run build

# Runner stage
FROM node:20-alpine AS runner
WORKDIR /app

# NODE_ENV is now set via docker-compose.yml to allow flexibility
# ENV NODE_ENV production  # Removed to allow runtime configuration
ENV NEXT_TELEMETRY_DISABLED 1

# Install runtime dependencies
RUN apk add --no-cache \
    openssl \
    wget

# Create non-root user
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 --ingroup nodejs nextjs

# Copy necessary files
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/package-lock.json ./package-lock.json

# Copy standalone build
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Copy Prisma files
COPY --from=builder /app/prisma ./prisma
COPY --from=builder /app/node_modules/.prisma ./node_modules/.prisma
COPY --from=builder /app/node_modules/@prisma ./node_modules/@prisma
COPY --from=builder /app/node_modules/prisma ./node_modules/prisma

# Copy entrypoint script
COPY --from=builder --chown=nextjs:nodejs /app/scripts/docker-entrypoint.sh ./scripts/
RUN chmod +x ./scripts/docker-entrypoint.sh

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["./scripts/docker-entrypoint.sh"]