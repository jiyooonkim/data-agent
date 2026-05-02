import requests

GROQ_API_KEY = "your_key"

def generate_sql(question):
    prompt = f"""
You are a SQL generator.

table: mart_ads_daily
columns: date, channel, product, campaign, spend, revenue, roas

Rules:
- only SELECT
- no DELETE, UPDATE
- use aggregation when needed

Question:
{question}

SQL:
"""

    res = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}]
        }
    )

    return res.json()["choices"][0]["message"]["content"]