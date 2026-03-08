# RAG Dataset

A curated collection of publicly available PDF documents for testing the Agentic RAG chatbot pipeline.

## Overview

This dataset contains 30 high-quality, text-based PDF documents organized into four categories:

| Category | Description | Count |
|----------|-------------|-------|
| `research_papers/` | Academic papers from arXiv, NeurIPS, ACL, CVPR | 12 |
| `technical_reports/` | Government and agency reports (NIST, NASA, UN) | 6 |
| `company_reports/` | AI company whitepapers and technical reports | 6 |
| `documentation/` | Technical references, surveys, and guides | 6 |

All documents are publicly available, text-based (not scanned images), and suitable for knowledge retrieval testing.

## Quick Start

### 1. Download the Dataset

```bash
# From the repository root
python download_dataset.py
```

This will:
- Read PDF URLs from `list_of_pdf_sources.json`
- Download each PDF into the appropriate category folder
- Validate files are proper, text-based PDFs
- Generate a download report

### 2. (Optional) Preprocess for RAG

```bash
python preprocess_dataset.py
```

This will:
- Extract text from all downloaded PDFs
- Split documents into chunks (1000 chars with 200 overlap — matching the RAG pipeline defaults)
- Save chunks as JSON Lines with metadata

### 3. Use with the RAG Pipeline

Upload the PDFs through the API or UI:

```bash
# Via the API
for pdf in rag_dataset/**/*.pdf; do
    curl -X POST http://localhost:8000/upload -F "files=@$pdf"
done
```

Or drag-and-drop files in the frontend UI at `http://localhost:3000`.

## Configuration

### Download Script Options

```bash
python download_dataset.py --help

Options:
  --output-dir DIR    Root directory for the dataset (default: rag_dataset/)
  --sources FILE      Path to the PDF sources JSON file
  --retry N           Number of download retries per file (default: 3)
```

### Preprocessing Options

```bash
python preprocess_dataset.py --help

Options:
  --dataset-dir DIR      Path to the dataset directory (default: rag_dataset/)
  --output FILE          Output JSONL file path
  --chunk-size N         Chunk size in characters (default: 1000)
  --chunk-overlap N      Overlap between chunks (default: 200)
```

## Dataset Structure

```
rag_dataset/
├── research_papers/
│   ├── attention_is_all_you_need.pdf
│   ├── bert_paper.pdf
│   ├── gpt2_paper.pdf
│   ├── resnet_paper.pdf
│   ├── dropout_paper.pdf
│   ├── batch_normalization_paper.pdf
│   ├── adam_optimizer_paper.pdf
│   ├── generative_adversarial_nets.pdf
│   ├── word2vec_paper.pdf
│   ├── vit_vision_transformer.pdf
│   ├── retrieval_augmented_generation.pdf
│   └── llama2_paper.pdf
├── technical_reports/
│   ├── nist_ai_risk_framework.pdf
│   ├── nist_cybersecurity_framework.pdf
│   ├── white_house_ai_bill_of_rights.pdf
│   ├── cbo_federal_budget_outlook.pdf
│   ├── un_sdg_report.pdf
│   └── nasa_systems_engineering_handbook.pdf
├── company_reports/
│   ├── google_ai_principles.pdf
│   ├── microsoft_responsible_ai.pdf
│   ├── anthropic_constitutional_ai.pdf
│   ├── deepmind_alphafold_paper.pdf
│   ├── openai_gpt4_technical_report.pdf
│   └── google_gemini_report.pdf
├── documentation/
│   ├── python_pep8_style_guide.pdf
│   ├── chain_of_thought_prompting.pdf
│   ├── react_prompting.pdf
│   ├── vector_database_survey.pdf
│   ├── langchain_rag_survey.pdf
│   └── prompt_engineering_survey.pdf
├── download_report.json
├── preprocessed_dataset.jsonl
└── preprocessed_dataset_metadata.json
```

## Adding New Sources

Edit `list_of_pdf_sources.json` to add new PDF sources:

```json
{
  "name": "my_document.pdf",
  "url": "https://example.com/document.pdf",
  "title": "My Document Title",
  "source": "Source Organization",
  "description": "Brief description of the document"
}
```

Then re-run `python download_dataset.py`.

## Requirements

The scripts use dependencies already included in the project:

- `pypdf>=3.17.0` (PDF parsing and validation)
- `requests>=2.31.0` (HTTP downloads)

No additional dependencies are needed.

## Notes

- PDF files are **not** committed to the repository (they are in `.gitignore`)
- The download script is idempotent — re-running it will re-download all files
- Some URLs may become unavailable over time; check the download report for failures
- All PDFs are publicly available under their respective licenses
