# frontend/.npmrc tem engine-strict=true: node e npm precisam bater exato com
# o campo "engines" do package.json, senao `npm ci` recusa.
FROM node:24.19.0-slim

WORKDIR /app

RUN npm install -g npm@11.17.0

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# NODE_ENV=production so depois do build: o build precisa das devDependencies.
RUN npm run build
ENV NODE_ENV=production

USER node
EXPOSE 3000

CMD ["npm", "start"]
