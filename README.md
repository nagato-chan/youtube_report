# Generate Your Personal YouTube Report

## Getting Started

### 1. Install Python 3+

If you don't already have Python 3+ installed on your computer, download it from <https://www.python.org/downloads/>.

Tool that you need:

- pipenv

### Setup

```bash
pipenv install
```

Get your Youtube API Key and create a `keys.txt` located at the project directory. Then add the key.

### Launch

```bash
pipenv run python main.py
```

Head to <http://127.0.0.1:8000/docs> for OpenAPI Doc.

### Workflow

First, the takeout file will be uploaded to the server

Then, the server will unzip the file and parse data from the data.
It may take some time to process the file since it is required to request the Youtube API for video data. Once the data is prepared, it will be available to fetch.

Then frontend will process the visualization part and the report is ready.
