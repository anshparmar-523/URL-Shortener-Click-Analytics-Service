# URL Shortener & Click Analytics Service

A full-stack URL shortening service built with **Flask + SQLite**. Generates unique short codes, redirects users, tracks per-link click counts, and visualises engagement through a clean analytics dashboard.

## Features

- Shorten any URL instantly with a 6-character base-62 code
- **Custom short codes** — e.g. `localhost:5001/my-link`
- Duplicate URL detection — same URL always gets the same code
- **Per-link analytics page** with a 14-day click time-series chart
- One-click copy button for short links
- Delete links from dashboard
- 404 page for invalid codes

## Tech Stack

`Python` · `Flask` · `SQLite` · `HTML5` · `CSS3` · `Chart.js`

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5001**

## Project Structure

```
3_url_shortener/
├── app.py
├── requirements.txt
├── templates/
│   ├── index.html   # Dashboard — shorten form + links table
│   ├── stats.html   # Per-link analytics with line chart
│   └── 404.html
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/shorten` | POST | Create a new short link |
| `/<code>` | GET | Redirect to original URL (tracks click) |
| `/stats/<code>` | GET | Analytics page for a link |
| `/delete/<id>` | POST | Delete a link |
| `/api/clicks/<code>` | GET | JSON — last 14 days click data |
| `/api/top` | GET | JSON — top 5 links by clicks |
