FROM node:20-alpine

WORKDIR /usr/src/app

COPY package.json package-lock.json* ./
RUN npm install --production --ignore-scripts --no-audit

COPY . .

EXPOSE 8080

CMD ["node", "index.js"]
