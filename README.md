# outfox-health-technical-assessment-2025

Project Structure:
outfox-health-technical-assessment-2025/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── database.py          # Database connection & session
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── crud.py              # Database operations
│   ├── api/
│   │   ├── __init__.py
│   │   ├── providers.py     # /providers endpoint
│   │   └── ask.py           # /ask endpoint
│   └── services/
│       ├── __init__.py
│       ├── openai_service.py # OpenAI integration
│       └── search_service.py # Search logic
├── etl.py                   # Data loading script
├── requirements.txt         # Dependencies
├── docker-compose.yml       # Docker setup
├── Dockerfile              # App container
├── .env                    # Environment variables
├── .gitignore              # Git Ignore
├── README.md               # Documentation
└── migrations/             # Database migrations