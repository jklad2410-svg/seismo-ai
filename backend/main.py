import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="SeismoAI Neural Telemetry Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:your_neon_password@ep-cold-dawn-123456.us-east-2.aws.neon.tech/neondb?sslmode=require")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

@app.get("/")
def read_root():
    return {"status": "online", "system": "SeismoAI Neural Core", "version": "1.0.0"}

@app.get("/api/earthquakes")
def get_earthquakes(limit: int = 50, min_magnitude: float = 0.0):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM earthquakes 
            WHERE magnitude >= %s 
            ORDER BY time DESC 
            LIMIT %s
            """,
            (min_magnitude, limit)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"count": len(rows), "data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
def get_stats():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                COUNT(*) as total_events,
                ROUND(AVG(magnitude)::numeric, 2) as avg_magnitude,
                MAX(magnitude) as max_magnitude,
                SUM(CASE WHEN classification = 'CRITICAL THREAT' THEN 1 ELSE 0 END) as critical_count
            FROM earthquakes
        """)
        stats = cur.fetchone()
        cur.close()
        conn.close()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))