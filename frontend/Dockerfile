FROM oven/bun:1.4 AS build
WORKDIR /app
COPY package.json bun.lock bunfig.toml ./
RUN bun install --frozen-lockfile
COPY . .
# The browser calls the backend directly, so the URL is baked in at build time.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL NITRO_PRESET=node-server
RUN bun run build

FROM node:24-slim
WORKDIR /app
COPY --from=build /app/.output ./.output
ENV PORT=8080 HOST=0.0.0.0
EXPOSE 8080
CMD ["node", ".output/server/index.mjs"]
