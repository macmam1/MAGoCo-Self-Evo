# ===== Stage 1: Base =====
FROM node:20-alpine AS base

WORKDIR /app

# ===== Stage 2: Development =====
FROM base AS development

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy package files
COPY package.json ./
COPY pnpm-lock.yaml* ./

# Install deps
RUN pnpm install

# Copy source
COPY . .

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0"]

# ===== Stage 3: Build =====
FROM base AS build

RUN corepack enable && corepack prepare pnpm@latest --activate

COPY package.json ./
COPY pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# ===== Stage 4: Production =====
FROM nginx:1.27-alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
