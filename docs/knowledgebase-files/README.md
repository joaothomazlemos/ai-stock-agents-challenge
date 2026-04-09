# Knowledge base source documents

PDF documents used as the RAG knowledge base.

## Files

| File | Source |
|------|--------|
| `Amazon-2024-Annual-Report.pdf` | [Amazon IR](https://s2.q4cdn.com/299287126/files/doc_financials/2025/ar/Amazon-2024-Annual-Report.pdf) |
| `AMZN-Q3-2025-Earnings-Release.pdf` | [Amazon IR](https://s2.q4cdn.com/299287126/files/doc_financials/2025/q3/AMZN-Q3-2025-Earnings-Release.pdf) |
| `AMZN-Q2-2025-Earnings-Release.pdf` | [Amazon IR](https://s2.q4cdn.com/299287126/files/doc_financials/2025/q2/AMZN-Q2-2025-Earnings-Release.pdf) |

## Re-download

```bash
chmod +x docs/knowledgebase-files/download.sh
./docs/knowledgebase-files/download.sh
```

If `curl` returns HTTP 403, open each URL in a browser and save the PDFs into this folder with the same filenames.
