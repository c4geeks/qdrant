# Qdrant Web UI Demo

Companion to: https://computingforgeeks.com/qdrant-web-ui-guide/

Helpers for loading data into Qdrant and capturing every panel of the Web UI.

## Files

- `load-sample-datasets.sh` — Recovers the three official sample snapshots
  (Midjourney Styles, Qdrant Web Documentation, Prefix Cache) into a running
  cluster via the snapshot recovery API. Same payload the dashboard's
  Datasets panel sends when you click *Import*.
- `capture-shots.py` — Playwright script that screenshots every Web UI
  panel at 1440×900. Handles the Visualize / Graph panels that require a
  RUN-button click before they render.

## Quickstart

Spin up Qdrant (Docker), load the sample datasets, then capture the UI:

```bash
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant:latest
sleep 5
./load-sample-datasets.sh

# Capture all panels (headless)
python3 -m venv venv && . venv/bin/activate
pip install playwright
playwright install chromium
python3 capture-shots.py
ls -lh shots/
```

## Authenticated clusters

If your server has `QDRANT__SERVICE__API_KEY` set, export the key first:

```bash
export QDRANT_API_KEY="your-service-key"
./load-sample-datasets.sh
```

For remote clusters, point the loader and capture script at the right host:

```bash
QDRANT_URL=http://10.0.1.50:6333 ./load-sample-datasets.sh
python3 capture-shots.py --host http://10.0.1.50:6333 --collection midlib
```

## Routes covered

| Output PNG | Route |
|---|---|
| `01-collections.png` | `/dashboard#/` |
| `02-welcome.png` | `/dashboard#/welcome` |
| `03-console.png` | `/dashboard#/console` |
| `04-datasets.png` | `/dashboard#/datasets` |
| `05-collection-detail.png` | `/dashboard#/collections/<name>` |
| `06-visualize.png` | `/dashboard#/collections/<name>/visualize` |
| `07-graph.png` | `/dashboard#/collections/<name>/graph` |
| `08-tutorial-index.png` | `/dashboard#/tutorial` |
| `09-tutorial-filtering.png` | `/dashboard#/tutorial/filteringbeginner` |
| `10-access-tokens.png` | `/dashboard#/jwt` |

Tutorial slugs are no-hyphen lowercase. A hyphenated slug
(`filtering-beginner`) resolves to a blank page because React Router never
matches it.

## Notes from real use

- The Access Tokens panel renders but cannot sign JWTs unless the server
  has an API key configured. The sidebar shows it greyed out otherwise.
- Visualize and Graph run their dimensionality-reduction work in the
  browser. The default 500-point sample is small for a reason; ramping
  `limit` past ~10k freezes the tab.
- Image previews in the Graph and Collection-detail panels only render
  when the payload field is literally named `image_url`. If your payload
  uses `img`, `thumbnail`, or `asset_url`, the preview area stays blank.
- Tutorials write real collections (`terraforming`, `star_charts`) to
  your cluster. Clean up with `DELETE collections/<name>` when done.
