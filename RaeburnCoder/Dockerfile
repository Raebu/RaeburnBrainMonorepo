# Simple multi-stage Dockerfile for Code Assistant
FROM node:20 AS build
WORKDIR /app
# install backend deps
COPY code-assistant/backend/package*.json ./code-assistant/backend/
RUN cd code-assistant/backend && npm ci
# install frontend deps and build
COPY code-assistant/frontend/package*.json ./code-assistant/frontend/
RUN cd code-assistant/frontend && npm ci && npm run build
# copy source
COPY code-assistant ./code-assistant
# move frontend build into backend public folder
RUN mkdir -p code-assistant/backend/public && cp -r code-assistant/frontend/dist code-assistant/backend/public/dist

FROM node:20 AS runner
WORKDIR /app
COPY --from=build /app/code-assistant/backend ./code-assistant/backend
WORKDIR /app/code-assistant/backend
ENV NODE_ENV=production
EXPOSE 3001
CMD ["node", "server.js"]
