FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

COPY --chown=nodejs:nodejs . .

RUN npm run build

# Install serve to serve static files
RUN npm install -g serve

# Change ownership of the app directory
RUN chown -R nodejs:nodejs /app

# Switch to non-root user
USER nodejs

EXPOSE 3000

# Serve the static export
CMD ["serve", "-s", "out", "-l", "3000"]