FROM node:22-alpine
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
ENV NEXT_PUBLIC_API_URL=http://localhost:8000
RUN pnpm build
EXPOSE 3000
CMD ["pnpm", "start"]
