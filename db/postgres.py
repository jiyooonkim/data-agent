import psycopg2

conn = psycopg2.connect(
    host="localhost",
    dbname="ads",
    user="postgres",
    password="1234"
)

def run_query(sql):
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()

def insert_rows(df):
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO mart_ads_daily
                (date, channel, product, campaign, spend, revenue, roas)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, tuple(row))
        conn.commit()