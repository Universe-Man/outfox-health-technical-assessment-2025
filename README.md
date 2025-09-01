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





# Healthcare Cost Navigator

A FastAPI-based web service that enables patients to search for hospitals offering MS-DRG procedures, view estimated prices & quality ratings, and interact with an AI assistant for natural language queries about healthcare costs.

## Features

- **Hospital Search**: Find hospitals by DRG procedure code and location
- **Geographic Search**: Search within specified radius of ZIP code
- **AI Assistant**: Natural language queries about costs and ratings
- **Cost Comparison**: Compare average charges across providers
- **Quality Ratings**: View mock star ratings (1-10 scale) for hospitals

## Tech Stack

- **Backend**: Python 3.11, FastAPI, async SQLAlchemy
- **Database**: PostgreSQL with geographic search capabilities
- **AI**: OpenAI GPT-3.5-turbo for natural language processing
- **Geocoding**: Geopy for ZIP code to coordinate conversion
- **Containerization**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- OpenAI API key
- `sample_prices_ny.csv` file (download from provided link)

### 1. Setup Environment

```bash
# Clone or create the project directory
mkdir healthcare-cost-navigator
cd healthcare-cost-navigator

# Create environment file
cp .env.example .env
# Edit .env and add your OpenAI API key:
# OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 2. Download Data

Download `sample_prices_ny.csv` from the provided link and place it in the project root directory.

### 3. Start Services

```bash
# Start PostgreSQL and the API
docker-compose up -d

# Check if services are running
docker-compose ps
```

### 4. Load Data

```bash
# Run ETL script to load CSV data
docker-compose exec app python etl.py
```

### 5. Test the API

The API will be available at `http://localhost:8000`

- Interactive docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## API Endpoints

### GET /providers

Search hospitals by DRG procedure and location.

**Parameters:**
- `drg` (optional): DRG code or description (e.g., "470" or "joint replacement")
- `zip` (optional): ZIP code for location-based search
- `radius_km` (optional): Search radius in kilometers (default: 25)
- `limit` (optional): Maximum results (default: 20, max: 100)

**Example cURL commands:**

```bash
# Search for joint replacement procedures
curl "http://localhost:8000/providers?drg=470"

# Search near specific ZIP code
curl "http://localhost:8000/providers?drg=joint&zip=10001&radius_km=25"

# Search by procedure description
curl "http://localhost:8000/providers?drg=heart%20surgery&zip=10032&radius_km=40"
```

**Example Response:**
```json
{
  "hospitals": [
    {
      "provider_id": "330123",
      "provider_name": "NYC Health + Hospitals/Bellevue",
      "provider_city": "New York",
      "provider_state": "NY",
      "distance_km": 2.1,
      "average_covered_charges": 45230.50,
      "average_rating": 8.2,
      "total_discharges": 156
    }
  ],
  "total_count": 15
}
```

### POST /ask

Natural language interface for healthcare cost queries.

**Request Body:**
```json
{
  "question": "Who is cheapest for DRG 470 within 25 miles of 10001?"
}
```

**Example cURL commands:**

```bash
# Cost comparison query
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "Who is cheapest for DRG 470 within 25 miles of 10001?"}'

# Quality/ratings query
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "Which hospitals have the best ratings for heart surgery near 10032?"}'

# General procedure cost query
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "What are the average costs for knee replacement in New York?"}'

# Volume/experience query
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "Which hospital does the most joint replacements in NYC?"}'

# Out-of-scope query (for testing)
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is the weather today?"}'
```

**Example Response:**
```json
{
  "question": "Who is cheapest for DRG 470 within 25 miles of 10001?",
  "answer": "Based on the data, NYC Health + Hospitals/Bellevue offers the lowest average charges of $45,230 for Major Joint Replacement procedures within 25 miles of 10001.",
  "data_source": "database_query"
}
```

## AI Assistant Capabilities

The AI assistant can handle various types of healthcare-related queries:

### 5+ Example Prompts

1. **Cost Comparison**: 
   - "Who is cheapest for DRG 470 within 25 miles of 10001?"
   - "What are the lowest cost hospitals for heart surgery near 10032?"

2. **Quality/Ratings Queries**:
   - "Which hospitals have the best ratings for joint replacement?"
   - "Show me the highest rated cardiac surgery centers in New York"

3. **Procedure-Specific Searches**:
   - "Find knee replacement costs near 10001"
   - "What hospitals do hip replacements in Manhattan?"

4. **Volume/Experience Queries**:
   - "Which hospital performs the most joint replacements?"
   - "Show me high-volume cardiac surgery centers"

5. **Geographic Comparisons**:
   - "Compare heart surgery costs between NYC hospitals"
   - "What are average procedure costs in different ZIP codes?"

6. **Out-of-Scope Handling**:
   - "What's the weather today?" → "I can only help with hospital pricing and quality information."

## Database Schema

### Providers Table
- `provider_id`: Unique CMS provider identifier
- `provider_name`: Hospital name
- `provider_city/state/zip_code`: Location information
- `latitude/longitude`: Geographic coordinates for radius searches
- `ms_drg_definition`: Procedure description
- `total_discharges`: Volume indicator
- `average_covered_charges`: Hospital's average bill
- `average_total_payments`: Total payments received
- `average_medicare_payments`: Medicare portion

### Ratings Table
- `provider_id`: Links to providers table
- `rating`: Star rating (1-10 scale)

### Indexes
- ZIP code index for location searches
- Text search index on DRG definitions
- Geographic index on latitude/longitude
- Foreign key index on provider relationships

## Architecture Decisions

### 1. **Async FastAPI + SQLAlchemy**
- **Choice**: Async throughout the stack
- **Rationale**: Better performance for I/O-bound operations (database queries, API calls)
- **Trade-off**: Slightly more complex code vs. better scalability

### 2. **OpenAI Integration Strategy**
- **Choice**: GPT-3.5-turbo for NL→SQL conversion
- **Rationale**: Cost-effective, good performance for structured queries
- **Trade-off**: External dependency vs. sophisticated natural language understanding

### 3. **Geographic Search Implementation**
- **Choice**: Haversine distance calculation in SQL + Geopy for geocoding
- **Rationale**: Simple, works with standard PostgreSQL
- **Trade-off**: Less efficient than PostGIS but easier to set up

### 4. **Mock Ratings Generation**
- **Choice**: Random ratings with realistic distribution
- **Rationale**: Creates realistic test data for demonstrations
- **Alternative**: Could integrate actual CMS star ratings

### 5. **Error Handling Strategy**
- **Choice**: Graceful degradation with informative messages
- **Rationale**: Better user experience when external services fail
- **Implementation**: Fallback responses, detailed logging

## Development Setup

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL locally
createdb healthcare_cost_navigator

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://user:password@localhost/healthcare_cost_navigator"
export OPENAI_API_KEY="your_key_here"

# Run ETL
python etl.py

# Start API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
# Basic functionality test
curl http://localhost:8000/health

# Test providers endpoint
curl "http://localhost:8000/providers?drg=470&zip=10001"

# Test AI assistant
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is the cheapest hospital for joint replacement?"}'
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check if PostgreSQL is running
   docker-compose ps
   
   # Check logs
   docker-compose logs db
   ```

2. **ETL Geocoding Slow**
   - The ETL process geocodes ZIP codes which can take time
   - Progress is logged every 50 ZIP codes
   - Consider reducing dataset size for testing

3. **OpenAI API Errors**
   - Verify API key is set correctly in `.env`
   - Check API quota/billing status
   - Review logs for specific error messages

4. **Out of Memory During ETL**
   - Process CSV in chunks if dataset is very large
   - Increase Docker memory limits if needed

### Performance Optimization

- Add database connection pooling for production
- Implement caching for frequent geocoding requests  
- Consider PostGIS extension for better geographic queries
- Add database indexes for common query patterns

## Future Enhancements

- [ ] Integration with real CMS star ratings
- [ ] More sophisticated fuzzy matching for procedures
- [ ] Caching layer (Redis) for improved performance
- [ ] User authentication and personalized queries
- [ ] Export functionality (CSV, PDF reports)
- [ ] Advanced analytics and trending

## License

This project is for assessment purposes.

---

**Assessment Notes**: This implementation focuses on core functionality within the 4-hour timeframe. Production deployment would require additional security, monitoring, and performance optimizations.