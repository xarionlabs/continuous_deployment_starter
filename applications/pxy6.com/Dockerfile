FROM node:20-alpine AS build

WORKDIR /app

COPY . .

WORKDIR /app/src

RUN npm install --legacy-peer-deps --include=dev

RUN chmod +x /app/entrypoints/entrypoint.sh

ENTRYPOINT ["/app/entrypoints/entrypoint.sh"]