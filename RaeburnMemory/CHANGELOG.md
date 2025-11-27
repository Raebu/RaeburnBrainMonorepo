# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
- Documentation built with MkDocs and deployed to GitHub Pages
- Added a mermaid data flow diagram and API reference

- Initial package structure and tests
- Added MIT license and aligned HTTPX version with FastAPI
- Aligned Python version support with CI (Python 3.9+)
- Updated dependency pins: FastAPI 0.110.0, Starlette 0.36.3 and HTTPX 0.27.0 for compatibility
- Upgraded FAISS to 1.11.0.post1 and use `faiss.write_index` for persistence
- Improved SQLite backend with WAL mode and automatic connection closing
- Bumped FastAPI to 0.111.0 with Starlette 0.37.2 and HTTPX 0.28.1 to match modern deployments
- Replaced the minimal CLI with a Typer application providing ``add``, ``export`` and ``similar`` commands
- Added dataclass-based node models and async helpers for batch persistence
- Integrated an optional Qdrant vector backend with connection pooling
- Embedding model can be configured via `RAEBURN_EMBED_MODEL`
- API endpoints require `RAEBURN_API_KEY` and enforce optional rate limiting
- Endpoints are async for better scalability
- Optional feature extras defined in `pyproject.toml`
- CI now pushes git tags automatically when commits land on main
