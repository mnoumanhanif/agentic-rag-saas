"""Main entry point for the Agentic RAG system."""

import logging

import uvicorn

from rag_system.config.settings import get_settings


def main():
    """Start the Agentic RAG API server."""
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Agentic RAG System v2.0.0")
    logger.info("API server at http://%s:%d", settings.api.host, settings.api.port)

    # Import here to avoid triggering pipeline init at module load
    from rag_system.api.server import get_app

    app = get_app()
    uvicorn.run(
        app,
        host=settings.api.host,
        port=settings.api.port,
    )


if __name__ == "__main__":
    main()
