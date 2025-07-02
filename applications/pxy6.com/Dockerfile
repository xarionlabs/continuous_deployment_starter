FROM node:20-alpine AS build

WORKDIR /app

COPY . .

WORKDIR /app/src

RUN npm install --legacy-peer-deps --include=dev

RUN chmod +x entrypoints/entrypoint.sh

ENTRYPOINT ["entrypoints/entrypoint.sh"]