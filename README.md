# Dockerize OpenClaw CLI Gateway Stack

Docker & Docker Compose setup untuk menjalankan stack [openclaw-cli-gateway-stack](https://github.com/everflowinv/openclaw-cli-gateway-stack.git).

Stack ini mengubah subscription-backed coding CLIs (**Claude Code**, **Google Antigravity**, dan **Muse Code**) menjadi local OpenAI-compatible model provider untuk [OpenClaw](https://openclaw.ai), lengkap dengan live SSE log viewer dan OpenClaw MCP proxy.

---

## 🏛️ Komponen & Port

| Service | Port | Keterangan |
|---|---|---|
| **`claude-cli-gateway`** | `4568` | OpenAI-compatible endpoint yang memanggil `claude -p --stream-json` |
| **`antigravity-cli-gateway`** | `4569` | OpenAI-compatible endpoint yang memanggil `agy` print mode |
| **`antigravity-websearch`** | `4570` | Gemini-compatible web search provider via Antigravity `search_web` |
| **`muse-cli-gateway`** | `4571` | OpenAI-compatible endpoint yang memanggil Muse Code |
| **`live-log-viewer`** | `8765` | Web dashboard (SSE) untuk memantau logs gateway secara real-time |
| **`openclaw-mcp-proxy`** | *(stdio)* | Bridge MCP yang mengekspos tools OpenClaw ke dalam CLI |

---

## 🚀 Quick Start

### 1. Persiapan File Environment
Salin template konfigurasi:
```bash
cp .env.example .env
```

Sesuaikan path credential di file `.env` jika berbeda dari lokasi default:
```env
# Path credential di host machine
HOST_CLAUDE_CONFIG=~/.claude
HOST_CLAUDE_JSON=~/.claude.json
HOST_GEMINI_CONFIG=~/.gemini
HOST_MUSE_AUTH=~/.config/muse/auth.json
HOST_WORKSPACE_PATH=./workspace
```

### 2. Jalankan Stack
Cukup jalankan Docker Compose:
```bash
docker compose up -d
```

Docker Compose akan otomatis:
1. Mem-build image container berbasis Node.js 22 LTS & Python 3.
2. Meng-clone repositori upstream `https://github.com/everflowinv/openclaw-cli-gateway-stack.git`.
3. Meng-install Claude Code CLI secara global.
4. Menyiapkan konfigurasi MCP bridge secara otomatis.
5. Menjalankan seluruh gateway dan live log viewer.

### 3. Setup Khusus Antigravity CLI (Host Mode)
Jika `agy` (Antigravity CLI) dan `openclaw` berjalan di **host machine (macOS)**:

1. Jalankan daemon bridge di host agar container Docker dapat mengeksekusi `agy` host:
   ```bash
   python3 scripts/host_agy_daemon.py
   ```
2. Jalankan container Docker:
   ```bash
   docker compose up -d
   ```
3. Uji koneksi gateway seolah-olah dari OpenClaw:
   ```bash
   # Test cepat (Health check + Non-streaming turn)
   python3 scripts/test_openclaw.py

   # Test streaming SSE (seperti saat OpenClaw generate teks langsung)
   python3 scripts/test_openclaw.py --stream

   # Jalankan semua pengujian (Health, Models, Chat, Streaming, JSON output)
   python3 scripts/test_openclaw.py --all
   ```

### 4. Verifikasi Status & Health Checks
Buka browser atau cek endpoint kesehatan:
- **Antigravity Gateway Health**: `curl http://localhost:4569/health`
- **Antigravity Websearch Health**: `curl http://localhost:4570/health`
- **Live Log Viewer**: [http://localhost:8765](http://localhost:8765)

---

## 🔑 Autentikasi CLI Tools

Karena gateway menggunakan CLI resmi dengan kuota langganan akun Anda, container memerlukan akses ke sesi login host:

- **Claude Code**: Memerlukan file `~/.claude.json` dan folder `~/.claude/` yang telah di-login (`claude login` di host).
- **Google Antigravity (`agy`)**: Memerlukan token kredensial dari `~/.gemini/` atau `~/.config/antigravity`.
- **Muse Code**: Memerlukan token dari `~/.config/muse/auth.json`.

Jika Anda hanya menggunakan Claude Code, Anda dapat menonaktifkan service lain di `.env`:
```env
ENABLE_CLAUDE=1
ENABLE_ANTIGRAVITY=0
ENABLE_WEBSEARCH=0
ENABLE_MUSE=0
ENABLE_LOG_VIEWER=1
```

---

## 🧩 Mode Pengoperasian

### Mode 1: All-In-One (Default)
Satu container ringan yang mengelola semua gateway via process supervisor bawaan. Menghemat memori RAM (~150MB total) dan file logs otomatis sinkron ke Live Log Viewer.
```bash
docker compose up -d
```

### Mode 2: Microservices Profile
Jika Anda ingin tiap gateway berjalan di container terisolasi:
```bash
docker compose --profile microservices up -d
```
Atau hanya menjalankan service tertentu:
```bash
docker compose --profile microservices up -d claude-gateway log-viewer
```

---

## 🔌 Menghubungkan ke OpenClaw

Di konfigurasi OpenClaw (`~/.openclaw/config.yaml` atau UI model provider), daftarkan provider OpenAI-compatible:

```yaml
models:
  providers:
    claude-gateway:
      type: openai-completions
      baseUrl: http://127.0.0.1:4568/v1
      apiKey: "sk-local"
    antigravity-gateway:
      type: openai-completions
      baseUrl: http://127.0.0.1:4569/v1
      apiKey: "sk-local"
    muse-gateway:
      type: openai-completions
      baseUrl: http://127.0.0.1:4571/v1
      apiKey: "sk-local"
```

---

## 🛠️ Perintah Berguna

```bash
# Melihat logs container
docker compose logs -f

# Restart container
docker compose restart

# Menghentikan stack
docker compose down

# Rebuild image setelah update upstream
docker compose build --no-cache
```
