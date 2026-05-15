# Subnautica 2 Save Sync

P2P game save synchronizer for Subnautica 2 - syncs saves between players via your own MinIO server.

## Setup

### 1. Start MinIO Server (on your VPS)
```bash
# SSH into your VPS, then:
export MINIO_ROOT_USER=minioadmin
export MINIO_ROOT_PASSWORD=minioadmin
./minio server /mnt/minio --console-address ":9001" &
```

Open `http://YOUR_VPS_IP:9001` in browser, login, create bucket named `subnautica2-saves`.

### 2. Download & Run
Download the latest release from the Releases page. Run the .exe.

### 3. Configure in App
- **MinIO Server**: `http://YOUR_VPS_IP:9000`
- **Access Key**: `minioadmin`
- **Secret Key**: `minioadmin`
- **Bucket**: `subnautica2-saves`
- **Player ID**: Choose a unique name (e.g., "player1")
- **Game Path**: Browse to your Subnautica2.exe
- **Save Dir**: Browse to `C:\Users\YOUR_USER\AppData\Local\Subnautica2\Saved\SaveGames`

### 4. Launch
Click **LAUNCH GAME** - the app will:
1. Pull latest save from cloud
2. Launch the game
3. After you close the game, upload your save to cloud
4. Release the lock so others can play

## How It Works
- Only one player can play at a time (lock prevents conflicts)
- Saves are synced automatically on launch/close
- Your MinIO server stores the save files and metadata