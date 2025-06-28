FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

RUN npm run build

# Install serve to serve static files
RUN npm install -g serve

EXPOSE 3000

# Serve the static export
CMD ["serve", "-s", "out", "-l", "3000"]