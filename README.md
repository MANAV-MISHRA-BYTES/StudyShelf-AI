# StudyShelf AI

StudyShelf AI turns a messy folder of study PDFs into an organized, searchable shelf using a local open-weight AI model.

## Why I built it

A friend I know keeps study material scattered across dozens or hundreds of PDFs. Finding the right document and remembering what each file contains is surprisingly difficult. StudyShelf AI was built to make that folder useful without requiring the documents to be uploaded to a third-party AI service.

## Features

- Batch PDF upload
- Local PDF text extraction
- AI-generated subject/category
- AI-generated tags
- Priority classification
- Short document summaries
- Search across the organized shelf
- CSV study index export
- Local AI inference through LM Studio

## Open-source AI

The application is designed around a locally running open-weight model exposed by LM Studio. The model is the component that understands each document and produces its organization metadata. Because inference happens locally, the study PDFs can remain on the user's machine instead of being sent to a hosted AI API.

## Run locally

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

Start LM Studio's local server first and load an open-weight instruct model. Then enter the model name shown by LM Studio in the sidebar.

Default server URL:

`http://localhost:1234`

## Demo

WILL UPLOAD!

## Challenge

Built for the DEV Community Hacktoberfest Weekend Challenge: **Build for a Friend**.
