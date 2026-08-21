# 10 — DEPLOYMENT AND INSTALLATION GUIDE
### ระบบ TOR Generator — คู่มือติดตั้งและ Deploy (PoC → Production)

> **แอปที่รันจริงตอนนี้ใช้ Docker + FastAPI + Next.js**  
> ติดตั้งตาม `14-INSTALLATION.md` ไม่ใช้ไฟล์ HTML ด้านล่างเป็น runtime  
> คู่มือผู้ใช้ปัจจุบัน: `13-USER_GUIDELINE.md` (ภาพ Playwright 21 ส.ค. 2026)  
> เดโม UX/UI ที่คลิกได้: https://chiraleo2000.github.io/tor-generator/ (`index.html` ที่ราก) — ไม่ใช่ `06-UXUI-Mockup.html`

---

## สารบัญ

1. [รันต้นแบบ PoC ในเครื่อง (Local Demo)](#1-รันต้นแบบ-poc-ในเครื่อง-local-demo)
2. [ข้อกำหนดระบบสำหรับ Production](#2-ข้อกำหนดระบบสำหรับ-production)
3. [ตัวแปรสภาพแวดล้อม (Environment Variables)](#3-ตัวแปรสภาพแวดล้อม-environment-variables)
4. [ติดตั้งด้วย Docker Compose (Local/Staging)](#4-ติดตั้งด้วย-docker-compose-localstaging)
5. [Dockerfile — Frontend & Backend](#5-dockerfile--frontend--backend)
6. [Database Migration](#6-database-migration)
7. [Deploy สู่ Kubernetes (Production)](#7-deploy-สู่-kubernetes-production)
8. [CI/CD Pipeline](#8-cicd-pipeline)
9. [Health Checks & Monitoring](#9-health-checks--monitoring)
10. [Security Checklist](#10-security-checklist)
11. [Rollback Procedure](#11-rollback-procedure)

---

## 1. รันต้นแบบ PoC ในเครื่อง (Local Demo)

ไฟล์ `06-UXUI-Mockup.html` เป็น **Single-file HTML application** ไม่ต้อง build หรือติดตั้ง dependency ใดๆ

### วิธีที่ 1 — เปิดตรงจาก Browser (ง่ายที่สุด)

1. ดับเบิลคลิกไฟล์ `06-UXUI-Mockup.html` หรือเปิดผ่านเบราว์เซอร์ (Chrome/Edge/Firefox แนะนำเวอร์ชันล่าสุด)
2. **สำคัญ:** ต้องมีการเชื่อมต่ออินเทอร์เน็ต เพราะระบบโหลดไลบรารี OCR จาก CDN ณ ตอนเปิดหน้า:
   - `pdf.js` จาก cdnjs.cloudflare.com
   - `mammoth.js` จาก unpkg.com
   - `Tesseract.js` จาก cdn.jsdelivr.net
3. เข้าสู่ระบบด้วย Demo Account ที่แสดงในหน้า Login: `demo@example.com` / `demo123`

### วิธีที่ 2 — รันผ่าน Local Web Server (แนะนำ ถ้าเจอปัญหา CORS ตอนอ่านไฟล์)

```bash
# Python 3
cd /path/to/folder
python3 -m http.server 8080
# เปิดเบราว์เซอร์ที่ http://localhost:8080/06-UXUI-Mockup.html

# หรือใช้ Node.js
npx serve .
```

### ข้อจำกัดของ PoC ที่ควรทราบ

- **ไม่มีการบันทึกข้อมูลถาวร** — ข้อมูลทั้งหมด (ผู้ใช้ที่สมัคร, โครงการที่สร้าง) อยู่ใน JavaScript memory เท่านั้น รีเฟรชหน้าแล้วข้อมูลจะรีเซ็ต
- หากเครือข่ายปิดกั้นการเข้าถึง CDN (เช่น องค์กรที่มี Firewall เข้มงวด) ฟังก์ชัน OCR จะแสดงข้อความ "สกัดข้อความล้มเหลว" แต่ระบบจะไม่ล้ม (Graceful Degradation) — ผู้ใช้ยังกรอกข้อมูลเองในฟอร์มได้ตามปกติ

---

## 2. ข้อกำหนดระบบสำหรับ Production

| องค์ประกอบ | เวอร์ชันขั้นต่ำที่แนะนำ |
|---|---|
| Node.js | 20.x LTS |
| PostgreSQL | 15+ |
| Redis | 7.x |
| Qdrant (หรือ PostgreSQL+pgvector) | 1.9+ |
| Docker | 24+ |
| Kubernetes (ถ้าใช้) | 1.28+ |
| RAM ต่อ Backend instance | 2 GB (4 GB ถ้ารัน OCR Worker ร่วม) |
| Storage สำหรับไฟล์ต้นฉบับ | ขึ้นกับปริมาณ TOR ที่คาดว่าจะอัปโหลด (แนะนำ Object Storage ไม่ใช้ Local Disk) |

---

## 3. ตัวแปรสภาพแวดล้อม (Environment Variables)

```bash
# ===== backend/.env =====
NODE_ENV=production
PORT=4000

# Database
DATABASE_URL=postgresql://tor_user:CHANGE_ME@postgres:5432/tor_generator

# Redis (session cache + BullMQ queue)
REDIS_URL=redis://redis:6379

# Vector Store
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=CHANGE_ME

# Auth
JWT_SECRET=CHANGE_ME_TO_RANDOM_64_CHAR_STRING
JWT_EXPIRES_IN=86400
BCRYPT_SALT_ROUNDS=12

# File Upload
MAX_FILE_SIZE_MB=20
OBJECT_STORAGE_BUCKET=tor-generator-files
OBJECT_STORAGE_ENDPOINT=https://s3.ap-southeast-1.amazonaws.com
OBJECT_STORAGE_ACCESS_KEY=CHANGE_ME
OBJECT_STORAGE_SECRET_KEY=CHANGE_ME

# OCR (server-side ทดแทน CDN ของ PoC)
TESSERACT_LANG=tha+eng
OCR_TIMEOUT_MS=30000

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_UPLOAD_PER_MINUTE=10

# ===== frontend/.env =====
VITE_API_BASE_URL=https://api.tor-generator.go.th/api/v1
VITE_APP_ENV=production
```

> **หมายเหตุความปลอดภัย:** ห้าม commit ไฟล์ `.env` ที่มีค่าจริงเข้า Git — ใช้ Secret Manager ของ Cloud Provider (AWS Secrets Manager / HashiCorp Vault / Kubernetes Secrets) แทน

---

## 4. ติดตั้งด้วย Docker Compose (Local/Staging)

```yaml
# docker-compose.yml
version: "3.9"
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: tor_generator
      POSTGRES_USER: tor_user
      POSTGRES_PASSWORD: ${DB_PASSWORD:-devpassword}
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes:
      - qdrant_data:/qdrant/storage

  backend:
    build: ./apps/backend
    env_file: ./apps/backend/.env
    depends_on: [postgres, redis, qdrant]
    ports: ["4000:4000"]

  frontend:
    build: ./apps/frontend
    env_file: ./apps/frontend/.env
    depends_on: [backend]
    ports: ["3000:80"]

volumes:
  pg_data:
  qdrant_data:
```

```bash
docker compose up -d
docker compose logs -f backend    # ตรวจสอบ log ตอน startup
docker compose exec backend npm run migrate   # รัน DB migration (ดูหัวข้อ 6)
```

---

## 5. Dockerfile — Frontend & Backend

```dockerfile
# apps/backend/Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
COPY package*.json ./
EXPOSE 4000
CMD ["node", "dist/app.js"]
```

```dockerfile
# apps/frontend/Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

---

## 6. Database Migration

ใช้ Prisma เป็นตัวอย่าง (ปรับเป็น TypeORM/Knex ได้ตามมาตรฐานทีม) โดยโครงสร้างตารางอ้างอิงจาก ER Diagram ในเอกสาร 07:

```bash
cd apps/backend
npx prisma migrate dev --name init          # สร้าง migration แรก (dev)
npx prisma migrate deploy                    # รันบน production (idempotent)
npx prisma db seed                           # seed ข้อมูลตั้งต้น เช่น demo user, KB categories
```

**Seed data ที่แนะนำ** (ให้ตรงกับ PoC เพื่อ demo ต่อเนื่อง): demo user (`demo@example.com`), 3 โครงการตัวอย่าง (e-Payment/ปภ./BMA Market), 8 หมวด KB_CHUNKED พร้อมจำนวน chunk ตามข้อมูลจริงในองค์กร

---

## 7. Deploy สู่ Kubernetes (Production)

โครงสร้างสอดคล้องกับ Deployment Diagram ในเอกสาร 07 หัวข้อ 8

```yaml
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tor-backend
spec:
  replicas: 3
  selector:
    matchLabels: { app: tor-backend }
  template:
    metadata:
      labels: { app: tor-backend }
    spec:
      containers:
        - name: tor-backend
          image: registry.internal/tor-generator/backend:latest
          ports: [{ containerPort: 4000 }]
          envFrom:
            - secretRef: { name: tor-backend-secrets }
          resources:
            requests: { cpu: "250m", memory: "512Mi" }
            limits: { cpu: "1", memory: "1Gi" }
          readinessProbe:
            httpGet: { path: /health, port: 4000 }
            initialDelaySeconds: 5
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tor-ocr-worker
spec:
  replicas: 2
  template:
    spec:
      containers:
        - name: tor-ocr-worker
          image: registry.internal/tor-generator/ocr-worker:latest
          resources:
            requests: { cpu: "500m", memory: "1Gi" }
            limits: { cpu: "2", memory: "2Gi" }
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: tor-ocr-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: tor-ocr-worker
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
```

```bash
kubectl apply -f k8s/
kubectl rollout status deployment/tor-backend
```

---

## 8. CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Build & Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm ci
      - run: npm run test                 # unit test ของ NLPEngine/ReviewEngine — สำคัญเพราะเป็น Rule-based logic ที่ต้อง regression-test
      - run: npm run lint

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build & push backend image
        run: |
          docker build -t registry.internal/tor-generator/backend:${{ github.sha }} apps/backend
          docker push registry.internal/tor-generator/backend:${{ github.sha }}
      - name: Build & push frontend image
        run: |
          docker build -t registry.internal/tor-generator/frontend:${{ github.sha }} apps/frontend
          docker push registry.internal/tor-generator/frontend:${{ github.sha }}

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/tor-backend tor-backend=registry.internal/tor-generator/backend:${{ github.sha }}
          kubectl rollout status deployment/tor-backend --timeout=120s
```

**คำแนะนำเพิ่มเติม:** เนื่องจาก `NLPEngine_*` และ `ReviewEngine_*` เป็นตรรกะ Regex/Keyword ที่ **แก้ไขได้บ่อยตามระเบียบราชการที่เปลี่ยนแปลง** ควรมี Unit Test ที่ครอบคลุมทุก pattern (เช่น เคส "ร้อยละ 30" vs "30%") ก่อน deploy ทุกครั้ง เพื่อป้องกัน regression ในกฎที่ใช้ตรวจสอบความถูกต้องของ TOR

---

## 9. Health Checks & Monitoring

| Endpoint | ใช้สำหรับ |
|---|---|
| `GET /health` | Liveness probe — ตรวจว่า process ยังรันอยู่ |
| `GET /health/ready` | Readiness probe — ตรวจการเชื่อมต่อ DB/Redis/Qdrant |
| `GET /metrics` | Prometheus metrics (request count, latency, queue length) |

**สิ่งที่ควร Monitor เป็นพิเศษ** (เฉพาะของระบบนี้):
- **OCR extraction failure rate** — ถ้าสูงผิดปกติ อาจแปลว่าไลบรารี OCR ล้าสมัยหรือ Worker ทำงานผิดพลาด
- **Review Engine score distribution** — เพื่อตรวจสอบว่ากฎ (keyword dictionary) ยังทันสมัยกับรูปแบบ TOR จริงหรือไม่
- **Queue length ของ OCR job** — บ่งบอกว่าต้อง scale worker เพิ่มหรือไม่

---

## 10. Security Checklist

- [ ] HTTPS/TLS ทุก endpoint (ไม่มี HTTP fallback)
- [ ] Password hash ด้วย bcrypt (salt rounds ≥ 12) — **ไม่เก็บ plaintext เหมือน `DB_USERS[]` ใน PoC**
- [ ] JWT secret สุ่มความยาว ≥ 64 ตัวอักษร เก็บใน Secret Manager
- [ ] Rate limiting เปิดใช้งานทุก endpoint โดยเฉพาะ `/auth/login` (ป้องกัน brute force)
- [ ] Validate ไฟล์ที่อัปโหลด: ตรวจ MIME type จริง (ไม่เชื่อ extension อย่างเดียว) + สแกนไวรัส
- [ ] จำกัดขนาดไฟล์อัปโหลด (20MB) ทั้งฝั่ง Nginx/Ingress และ Application
- [ ] CORS กำหนด origin ที่อนุญาตเฉพาะ Frontend domain จริง
- [ ] Audit log การเข้าถึง/แก้ไขโครงการ TOR (ภาคราชการต้องการ Audit Trail)
- [ ] Backup PostgreSQL อัตโนมัติทุกวัน + ทดสอบ restore เป็นระยะ

---

## 11. Rollback Procedure

```bash
# Kubernetes: ย้อนกลับ deployment ก่อนหน้า
kubectl rollout undo deployment/tor-backend
kubectl rollout status deployment/tor-backend

# Database: หากมี migration ที่ทำให้เกิดปัญหา
npx prisma migrate resolve --rolled-back <migration_name>

# ตรวจสอบสถานะหลัง rollback
kubectl get pods -l app=tor-backend
curl https://api.tor-generator.go.th/health
```

**หลักการ:** เก็บ image tag ของทุก release (ผูกกับ git SHA) เพื่อให้ rollback ได้ทันทีโดยไม่ต้อง build ใหม่ และควร deploy แบบ Blue-Green หรือ Canary สำหรับระบบราชการที่ต้องการ Downtime ต่ำ

---
*เอกสาร 10 — Deployment and Installation Guide | ครอบคลุมทั้งการรัน PoC ในเครื่องและการ Deploy Production เต็มรูปแบบ*
