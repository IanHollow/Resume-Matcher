FROM node:22-bullseye
WORKDIR /usr/src/app

# 👇 this turns OFF production mode even if .npmrc tries to re‑enable it
ENV NODE_ENV=development \
    NPM_CONFIG_PRODUCTION=false

COPY package*.json ./
RUN npm ci
COPY . .

ENV CHOKIDAR_USEPOLLING=true WATCHPACK_POLLING=true
EXPOSE 3000
CMD ["npm","run","dev"]
