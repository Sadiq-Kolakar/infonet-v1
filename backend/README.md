# INFONET Backend API

Read-only FastAPI service exposing the INFONET CSE College Information Management System knowledge graph.

## Architecture & Principles
- **Read-Only**: Strictly `GET` endpoints. Read-access sessions (`execute_read`) only. No write Cypher.
- **Data Scoping**: Every query is scoped to `:InfonetManaged:Entity` and approved relationships (`AFFILIATED_WITH`, `HAS_LABORATORY`, `OFFERS_PROGRAM`, `IS_HOD_OF`).
- **Standardized Error Envelope**: Every application error conforms to `{"error": {"code": "...", "message": "...", "details": {}}}`.
- **Provenance & Uncertainty**: Retains source caveats, unverified claims, and user-confirmed overrides (e.g., Dr. R. Sumathi HOD assertion).

## Requirements
- Python 3.10+
- Running Neo4j 5+ database with loaded INFONET dataset

## Setup

1. **Virtual Environment**:
   ```bash
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in local credentials:
   ```dotenv
   NEO4J_URI=neo4j://127.0.0.1:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-local-password
   NEO4J_DATABASE=neo4j
   API_HOST=127.0.0.1
   API_PORT=8000
   INFONET_QUERY_TIMEOUT_S=5
   ```

4. **Run Server**:
   ```bash
   uvicorn infonet_api.app:app --host 127.0.0.1 --port 8000 --reload
   ```

5. **Run Tests**:
   ```bash
   pytest
   ```

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Service liveness, Neo4j connectivity, data loaded check (always HTTP 200) |
| `GET` | `/api/v1/summary` | Department overview, calculated entity & relationship counts |
| `GET` | `/api/v1/about` | Dataset/pipeline run metadata, MVP scope statements, known limitations |
| `GET` | `/api/v1/people` | Paginated and filtered people directory (`q`, `category`, `role_title`) |
| `GET` | `/api/v1/laboratories` | Paginated laboratory directory (`q`) |
| `GET` | `/api/v1/programs` | Paginated program directory (`q`, `level`) with conflict status |
| `GET` | `/api/v1/entities/{id}` | Full detail for any managed entity, with related links, observations, and notes |
| `GET` | `/api/v1/graph` | Whole graph in Cytoscape format with approved edge types |
| `GET` | `/api/v1/data-quality` | 5 open data-quality items (DQI-01..DQI-05) |
