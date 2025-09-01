# app/services/openai_service.py
import os
import json
import re
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging
from ..crud import execute_custom_query

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a helpful assistant for a healthcare cost database. You can answer questions about hospital procedures, costs, and ratings.

Available database tables:
- providers: provider_id, provider_name, provider_city, provider_state, provider_zip_code, latitude, longitude, ms_drg_definition, total_discharges, average_covered_charges, average_total_payments, average_medicare_payments
- ratings: provider_id, rating (1-10 scale)

Guidelines:
1. Only answer questions related to healthcare costs, procedures, hospital ratings, and locations
2. For questions asking for specific data, generate a SQL query to retrieve the information
3. For out-of-scope questions (weather, sports, etc.), respond with: "I can only help with hospital pricing and quality information."
4. When generating SQL, use JOIN operations to combine provider and rating data when needed
5. Always include provider_name and relevant cost/rating information in results
6. Limit results to 10 unless specifically asked for more

Example SQL patterns:
- Cost queries: SELECT provider_name, average_covered_charges FROM providers WHERE ms_drg_definition ILIKE '%keyword%'
- Rating queries: SELECT p.provider_name, AVG(r.rating) FROM providers p JOIN ratings r ON p.provider_id = r.provider_id WHERE p.ms_drg_definition ILIKE '%keyword%' GROUP BY p.provider_name
- Location queries: Include provider_city, provider_state in results

Respond with either:
- A SQL query if the question requires database lookup
- A direct answer if it's general healthcare information
- "OUT_OF_SCOPE" if the question is not healthcare-related"""


async def classify_and_process_query(question: str) -> Dict[str, Any]:
    """
    Use OpenAI to classify the question and generate appropriate response
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Question: {question}"},
            ],
            max_tokens=500,
            temperature=0.1,
        )

        ai_response = response.choices[0].message.content.strip()

        # Check if it's out of scope
        if "OUT_OF_SCOPE" in ai_response.upper():
            return {
                "type": "out_of_scope",
                "response": "I can only help with hospital pricing and quality information. Please ask about medical procedures, costs, or hospital ratings.",
            }

        # Check if it contains SQL
        if "SELECT" in ai_response.upper():
            sql_match = re.search(
                r"(SELECT.*?;?)", ai_response, re.IGNORECASE | re.DOTALL
            )
            if sql_match:
                sql_query = sql_match.group(1).strip()
                if sql_query.endswith(";"):
                    sql_query = sql_query[:-1]  # Remove trailing semicolon
                return {
                    "type": "sql_query",
                    "sql": sql_query,
                    "explanation": ai_response,
                }

        # Direct answer
        return {"type": "direct_answer", "response": ai_response}

    except Exception as e:
        logger.error(f"OpenAI API call failed: {str(e)}")
        return {
            "type": "error",
            "response": "I'm having trouble processing your question right now. Please try again later.",
        }


def format_query_results(results: list, question: str) -> str:
    """
    Format database query results into a natural language response
    """
    if not results:
        return "I couldn't find any matching hospitals or procedures for your query."

    # Determine response format based on question type
    question_lower = question.lower()

    if "cheapest" in question_lower or "lowest cost" in question_lower:
        # Sort by cost and show the cheapest options
        if "average_covered_charges" in results[0]:
            sorted_results = sorted(
                results, key=lambda x: float(x.get("average_covered_charges", 0))
            )
            top_results = sorted_results[:3]
            response = (
                "Based on the data, here are the most cost-effective options:\n\n"
            )
            for i, hospital in enumerate(top_results, 1):
                name = hospital.get("provider_name", "Unknown")
                cost = hospital.get("average_covered_charges", 0)
                city = hospital.get("provider_city", "")
                state = hospital.get("provider_state", "")
                location = f" in {city}, {state}" if city and state else ""
                response += f"{i}. {name}{location} - ${cost:,.2f}\n"
            return response

    elif "best rating" in question_lower or "highest rating" in question_lower:
        # Show highest rated hospitals
        if "avg" in str(results[0]).lower() or "rating" in str(results[0]):
            rating_key = None
            for key in results[0].keys():
                if "rating" in key.lower() or "avg" in key.lower():
                    rating_key = key
                    break

            if rating_key:
                sorted_results = sorted(
                    results, key=lambda x: float(x.get(rating_key, 0)), reverse=True
                )
                top_results = sorted_results[:3]
                response = "Here are the highest-rated hospitals for your query:\n\n"
                for i, hospital in enumerate(top_results, 1):
                    name = hospital.get("provider_name", "Unknown")
                    rating = hospital.get(rating_key, 0)
                    city = hospital.get("provider_city", "")
                    state = hospital.get("provider_state", "")
                    location = f" in {city}, {state}" if city and state else ""
                    response += f"{i}. {name}{location} - Rating: {rating:.1f}/10\n"
                return response

    # Generic response format
    if len(results) == 1:
        hospital = results[0]
        name = hospital.get("provider_name", "Hospital")
        response = f"Found information for {name}:\n"
        for key, value in hospital.items():
            if key != "provider_name" and value is not None:
                formatted_key = key.replace("_", " ").title()
                if "charges" in key or "payments" in key:
                    response += f"- {formatted_key}: ${value:,.2f}\n"
                elif "rating" in key:
                    response += f"- {formatted_key}: {value}/10\n"
                else:
                    response += f"- {formatted_key}: {value}\n"
        return response
    else:
        response = f"Found {len(results)} matching hospitals:\n\n"
        for i, hospital in enumerate(results[:5], 1):  # Limit to 5 for readability
            name = hospital.get("provider_name", "Unknown")
            city = hospital.get("provider_city", "")
            state = hospital.get("provider_state", "")
            location = f" in {city}, {state}" if city and state else ""

            # Add key information
            details = []
            if "average_covered_charges" in hospital:
                details.append(f"Cost: ${hospital['average_covered_charges']:,.2f}")
            if any("rating" in key.lower() for key in hospital.keys()):
                rating_key = next(
                    (k for k in hospital.keys() if "rating" in k.lower()), None
                )
                if rating_key:
                    details.append(f"Rating: {hospital[rating_key]:.1f}/10")

            detail_str = f" ({', '.join(details)})" if details else ""
            response += f"{i}. {name}{location}{detail_str}\n"

        if len(results) > 5:
            response += f"\n... and {len(results) - 5} more hospitals"

        return response


async def process_natural_language_query(
    question: str, db: AsyncSession
) -> Dict[str, str]:
    """
    Main function to process natural language queries about healthcare costs
    """
    # Step 1: Classify and process the query with OpenAI
    query_analysis = await classify_and_process_query(question)

    if query_analysis["type"] == "out_of_scope":
        return {"answer": query_analysis["response"], "data_source": "ai_response"}

    if query_analysis["type"] == "error":
        return {"answer": query_analysis["response"], "data_source": "error"}

    if query_analysis["type"] == "direct_answer":
        return {"answer": query_analysis["response"], "data_source": "ai_knowledge"}

    if query_analysis["type"] == "sql_query":
        try:
            # Step 2: Execute the generated SQL query
            sql_query = query_analysis["sql"]
            logger.info(f"Executing SQL query: {sql_query}")

            results = await execute_custom_query(db, sql_query)

            # Step 3: Format results into natural language
            formatted_response = format_query_results(results, question)

            return {"answer": formatted_response, "data_source": "database_query"}

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return {
                "answer": "I encountered an error while searching the database. Please try rephrasing your question or contact support if the issue persists.",
                "data_source": "error",
            }

    # Fallback
    return {
        "answer": "I'm not sure how to process that question. Please ask about hospital costs, ratings, or procedures.",
        "data_source": "fallback",
    }
