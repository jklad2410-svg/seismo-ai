import os
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:your_neon_password@ep-cold-dawn-123456.us-east-2.aws.neon.tech/neondb?sslmode=require")
USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"

def classify_earthquake(mag, depth, tsunami):
    if mag >= 6.0 or (mag >= 5.0 and tsunami == 1):
        return "CRITICAL THREAT"
    elif mag >= 4.5:
        return "HIGH WARNING"
    elif mag >= 3.0:
        return "ELEVATED"
    else:
        return "NORMAL MONITOR"

def run_etl():
    print(f"[{datetime.utcnow()}] Starting SeismoAI Telemetry Sync...")
    response = requests.get(USGS_URL)
    if response.status_code != 200:
        print(f"Failed to fetch USGS feed: {response.status_code}")
        return
    
    data = response.json()
    features = data.get("features", [])
    print(f"Retrieved {len(features)} live events from USGS.")

    records = []
    for f in features:
        props = f["properties"]
        geom = f["geometry"]
        coords = geom["coordinates"] # [longitude, latitude, depth]
        
        eq_id = f["id"]
        title = props.get("title")
        mag = props.get("mag")
        place = props.get("place")
        time = props.get("time")
        updated = props.get("updated")
        url = props.get("url")
        detail = props.get("detail")
        felt = props.get("felt")
        cdi = props.get("cdi")
        mmi = props.get("mmi")
        alert = props.get("alert")
        status = props.get("status")
        tsunami = props.get("tsunami", 0)
        sig = props.get("sig")
        net = props.get("net")
        code = props.get("code")
        ids = props.get("ids")
        sources = props.get("sources")
        types = props.get("types")
        nst = props.get("nst")
        dmin = props.get("dmin")
        rms = props.get("rms")
        gap = props.get("gap")
        mag_type = props.get("magType")
        eq_type = props.get("type")
        
        longitude = coords[0] if len(coords) > 0 else None
        latitude = coords[1] if len(coords) > 1 else None
        depth = coords[2] if len(coords) > 2 else None
        
        classification = classify_earthquake(mag or 0.0, depth or 0.0, tsunami or 0)

        records.append((
            eq_id, title, mag, place, time, updated, url, detail,
            felt, cdi, mmi, alert, status, tsunami, sig, net, code,
            ids, sources, types, nst, dmin, rms, gap, mag_type, eq_type,
            longitude, latitude, depth, classification
        ))

    if not records:
        print("No event records parsed.")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    upsert_query = """
        INSERT INTO earthquakes (
            id, title, magnitude, place, time, updated, url, detail,
            felt, cdi, mmi, alert, status, tsunami, sig, net, code,
            ids, sources, types, nst, dmin, rms, gap, mag_type, type,
            longitude, latitude, depth, classification
        ) VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            magnitude = EXCLUDED.magnitude,
            updated = EXCLUDED.updated,
            classification = EXCLUDED.classification,
            alert = EXCLUDED.alert;
    """
    
    try:
        execute_values(cur, upsert_query, records)
        conn.commit()
        print(f"Successfully synchronized {len(records)} entries into Neon PostgreSQL.")
    except Exception as e:
        conn.rollback()
        print(f"ETL Database exception: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_etl()