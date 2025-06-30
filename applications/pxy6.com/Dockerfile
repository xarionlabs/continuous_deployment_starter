# Build stage
FROM node:20-alpine AS build

# Set working directory
WORKDIR /app

# Copy source code first
COPY . .

# Set working directory to src where package.json is located
WORKDIR /app/src

# Install dependencies with legacy peer deps to handle peer dependency issues
RUN npm install --legacy-peer-deps

# Build the application from the src directory
RUN npm run build

# Production stage - serve static files
FROM busybox
COPY --from=build /app/src/dist /usr/share/nginx/html
COPY src/nginx.conf /etc/nginx/conf.d/default.conf
# This container just copies files and exits
CMD ["true"]