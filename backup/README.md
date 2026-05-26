# Backup, Snapshot, and Restore Qdrant Collections

Companion to: https://computingforgeeks.com/qdrant-backup-snapshot-restore/

End-to-end snapshot lifecycle for Qdrant 1.18.1: per-collection + full
snapshots, three restore paths, S3 sync with IAM-role auth, and a real
disaster-recovery drill.

## Files

| File | Purpose |
|---|---|
| `seed.py` | Seed a 1000-point articles + 200-point products collection for tests |
| `snapshot_suite.sh` | Create per-collection + full snapshots, capture sizes/checksums |
| `restore_suite.sh` | Restore three ways: in-place, new collection, HTTP URL |
| `s3_backup_restore.sh` | aws s3 sync upload, simulate disaster, restore from S3 |
| `qdrant-backup.sh` | Production-ready hourly backup script |
| `systemd/qdrant-backup.{service,timer}` | systemd unit + timer for hourly runs |
| `lifecycle.json` | S3 bucket lifecycle: Standard → IA(7d) → Glacier IR(30d) → expire(365d) |

## Setup

```bash
# 1. Qdrant up
sudo docker run -d --name qdrant --restart=always \
  -p 6333:6333 -p 6334:6334 \
  -v /opt/qdrant/storage:/qdrant/storage \
  -v /opt/qdrant/snapshots:/qdrant/snapshots \
  qdrant/qdrant:v1.18.1

# 2. Python venv
python3 -m venv venv && source venv/bin/activate
pip install 'qdrant-client[fastembed]>=1.18.0'
python3 seed.py

# 3. S3 bucket + IAM role attached to the EC2 instance
aws s3api create-bucket --region eu-west-1 \
  --bucket cfg-qdrant-snapshots \
  --create-bucket-configuration LocationConstraint=eu-west-1
aws iam put-role-policy --role-name cfg-qdrant-ec2-role \
  --policy-name s3-snapshots --policy-document file://s3pol.json
aws s3api put-bucket-lifecycle-configuration \
  --bucket cfg-qdrant-snapshots --lifecycle-configuration file://lifecycle.json

# 4. Wire the systemd timer
sudo cp qdrant-backup.sh /usr/local/bin/
sudo cp systemd/qdrant-backup.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now qdrant-backup.timer
```

## Measured results (Qdrant 1.18.1 / t3.small / S3 eu-west-1)

| Operation | Wall time | Output |
|---|---|---|
| Per-collection snapshot (1000 × 384-dim) | 90 ms | 3.9 MB tar |
| Per-collection snapshot (200 × 8-dim) | 56 ms | 132 KB tar |
| Full cluster snapshot | 200 ms | 4.1 MB tar |
| aws s3 sync (entire snapshots dir) | 2.1 s | 10 objects uploaded |
| Restore in place | 120 ms | 1000 points back |
| Restore to new collection | 190 ms | 1000 points cloned |
| Restore from HTTP URL | 215 ms | 1000 points fetched |
| Full disaster-recovery drill (delete + S3 cp + restore + verify) | < 3 s | 1000 points + matching payload |

## Gotchas these scripts catch

- **Per-collection snapshot files can disappear after a full snapshot.** Sync
  to S3 immediately after creation, not on a separate schedule.
- **Default `priority` is `replica`**, not `snapshot`. For DR, you almost
  always want `"priority":"snapshot"` to actually overwrite the collection.
- **Snapshot files are tar archives**, not raw segment files. Use the restore
  endpoint, not manual untar into `/qdrant/storage`.
- **Always exclude `tmp/*`** when syncing the snapshots directory. The
  staging dir contains partial files mid-write.
- **IAM role propagation takes 10-20 s** after attach. Add a sleep+poll
  before the first S3 call in provisioning scripts.

Tested 2026-05 on Ubuntu 24.04 + AWS CLI 2.34 + EC2 t3.small + S3 in
eu-west-1.
