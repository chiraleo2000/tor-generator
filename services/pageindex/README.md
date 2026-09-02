# PageIndex backend

This directory makes the integrated TOR repository self-contained. Docker
Compose builds it as a backend-only vectorless retrieval service; users work
through the TOR UI instead of a separate PageIndex UI.

The service needs these values in the repository root `.env`:

- `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` and `AZURE_DOCUMENT_INTELLIGENCE_KEY`
  for PDF OCR.
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_MODEL`, and
  `AZURE_OPENAI_API_VERSION` for verified PageIndex hierarchy generation.
- `PAGEINDEX_API_KEY` is optional locally and recommended outside a private
  Docker network.

Indexed documents are stored in the `pageindex_data` Docker volume. No vector
database or embedding model is used by this service.
