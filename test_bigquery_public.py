#!/usr/bin/env python3
"""Test with BigQuery public datasets."""

import asyncio
import os
from dotenv import load_dotenv
from server import run_query, list_tables

# Load environment variables
load_dotenv()

async def test_public_datasets():
    """Test with BigQuery public datasets."""
    print("Testing BigQuery MCP Server with Public Datasets")
    print("=" * 50)
    
    # 1. Query a public dataset - NYC Taxi Trips
    print("\n1. Querying NYC Taxi Trips (public dataset):")
    query = """
    SELECT 
        EXTRACT(YEAR FROM pickup_datetime) as year,
        COUNT(*) as trip_count,
        ROUND(AVG(trip_distance), 2) as avg_distance_miles,
        ROUND(AVG(fare_amount), 2) as avg_fare_usd
    FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2020`
    WHERE pickup_datetime BETWEEN '2020-01-01' AND '2020-01-31'
    GROUP BY year
    ORDER BY year
    """
    
    result = await run_query.fn(query=query, max_results=10)
    if result["success"]:
        print(f"   Query successful!")
        for row in result['rows']:
            print(f"   Year: {row['year']}, Trips: {row['trip_count']:,}, "
                  f"Avg Distance: {row['avg_distance_miles']} mi, "
                  f"Avg Fare: ${row['avg_fare_usd']}")
        print(f"   Bytes processed: {result['bytes_processed']:,}")
        print(f"   Bytes billed: {result['bytes_billed']:,}")
    else:
        print(f"   Error: {result['error']}")
    
    # 2. Query GitHub data
    print("\n2. Querying GitHub Archive (public dataset):")
    query = """
    SELECT 
        type as event_type,
        COUNT(*) as event_count
    FROM `githubarchive.day.20240101`
    GROUP BY type
    ORDER BY event_count DESC
    LIMIT 5
    """
    
    result = await run_query.fn(query=query)
    if result["success"]:
        print(f"   Top 5 GitHub event types on 2024-01-01:")
        for row in result['rows']:
            print(f"   - {row['event_type']}: {row['event_count']:,} events")
        print(f"   Bytes processed: {result['bytes_processed']:,}")
        print(f"   Bytes billed: {result['bytes_billed']:,}")
    else:
        print(f"   Error: {result['error']}")
    
    # 3. List tables in a public dataset
    print("\n3. Listing tables in bigquery-public-data.covid19_johns_hopkins_csse:")
    result = await list_tables.fn(
        dataset_id="bigquery-public-data.covid19_johns_hopkins_csse",
        max_results=5
    )
    if result["success"]:
        print(f"   Found {result['count']} tables (showing first 5):")
        for table in result['tables'][:5]:
            print(f"   - {table['table_id']}")
            if table['num_rows']:
                print(f"     Rows: {table['num_rows']:,}, Size: {table['num_bytes']:,} bytes")
    else:
        print(f"   Error: {result['error']}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_public_datasets())