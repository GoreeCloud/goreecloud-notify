FROM node:24.13.0-bookworm-slim@sha256:43b867a6987f82c2117f9235e469bd00e0fd83688e3506301709a018e7de6afd

WORKDIR /app

COPY package.json ./package.json
RUN npm install --ignore-scripts --no-audit --no-fund

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
