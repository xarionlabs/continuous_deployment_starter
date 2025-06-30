# Build stage
FROM node:20-alpine AS build

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY bun.lockb ./

# Install dependencies with legacy peer deps to handle peer dependency issues
RUN npm install --legacy-peer-deps

# Copy source code
COPY . .

# Build the application from the root directory
RUN npm run build

# Production stage - serve static files
FROM busybox
COPY --from=build /app/src/dist /usr/share/nginx/html
COPY src/nginx.conf /etc/nginx/conf.d/default.conf
# This container just copies files and exits
CMD ["true"]