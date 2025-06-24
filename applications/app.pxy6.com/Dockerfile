FROM node:18-bookworm
RUN apt-get update && apt-get install -y openssl curl

EXPOSE 3000

WORKDIR /app

ENV NODE_ENV=production

COPY src/ ./src/

COPY entrypoints/ ./entrypoints/
RUN chmod +x ./entrypoints/*.sh

WORKDIR /app/src
RUN npm ci --omit=dev

# For production we can enable the following
# RUN npm remove @shopify/cli

RUN npm run build

WORKDIR /app

CMD ["./entrypoints/entrypoint.sh"]
