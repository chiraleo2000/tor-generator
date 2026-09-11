# Dataset exports

Large zip archives are built on demand (not committed — see root `.gitignore`).

## Classic RAG + Quick MCP zip

```powershell
powershell -File documents/exports/build-rag-mcp-zip.ps1
# or: python documents/exports/build_rag_mcp_zip.py --version 0.4.0
```

Output: `documents/exports/tor-rag-mcp-dataset-v0.4.0.zip`

| Path inside zip | Source |
|-----------------|--------|
| `rag-pdfs/` | `documents/sources/การจัดซื้อจัดจ้าง/ข้อมูลดิบ/*.pdf` |
| `rag-json-chunks/` | Matching `documents/knowledge-base/*_tor_extract.json` |
| `mcp-amazon-quick/` | `app/infra/quick/*` |

## PN AWS EC2 dataset (S3 + Embed 4 + pn-ec2 configs)

```bash
python documents/exports/build_pn_aws_dataset.py --version 0.6.1
```

Output: `documents/exports/tor-pn-aws-dataset-v0.6.1.zip`

Includes PDFs/JSON, `pn/rag-groups.yaml`, `pn/env.example`, MCP quick files, Discussions 32–35, `DATASET_MANIFEST.json`.

Sync after extract (AWS CLI + `app/infra/pn-ec2/.env`):

```bash
# PN_DATASET_LOCAL_PATH=.../rag-pdfs
bash app/infra/pn-ec2/scripts/sync-dataset-to-s3.sh
```

Deploy package: `app/infra/pn-ec2/` · guide: `Discussions/35-AWS-PN-DEV-AND-DEPLOY.md`
