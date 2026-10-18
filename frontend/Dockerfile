FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Browser tests. The image's Playwright version must match @playwright/test in package-lock.json,
# so the bundled browsers are the ones the test runner expects.
FROM mcr.microsoft.com/playwright:v1.64.1-noble AS e2e
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
CMD ["npx", "playwright", "test"]

FROM nginx:1.29-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
