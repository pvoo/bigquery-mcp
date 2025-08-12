-- BigQuery MCP Server - Sample Queries
-- These queries demonstrate various BigQuery features and can be used with the run_query tool

-- ============================================
-- BASIC QUERIES
-- ============================================

-- Simple test query
SELECT 'Hello BigQuery' as greeting, CURRENT_TIMESTAMP() as current_time;

-- Get current project info
SELECT @@project_id as project_id;

-- ============================================
-- PUBLIC DATASETS - NYC TAXI
-- ============================================

-- Analyze taxi trips by hour
SELECT
    EXTRACT(HOUR FROM pickup_datetime) as hour,
    COUNT(*) as trips,
    ROUND(AVG(trip_distance), 2) as avg_distance,
    ROUND(AVG(fare_amount), 2) as avg_fare
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2020`
WHERE DATE(pickup_datetime) = '2020-01-01'
GROUP BY hour
ORDER BY hour;

-- Top pickup locations
SELECT
    pickup_location_id,
    COUNT(*) as pickup_count
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2020`
WHERE DATE(pickup_datetime) BETWEEN '2020-01-01' AND '2020-01-07'
GROUP BY pickup_location_id
ORDER BY pickup_count DESC
LIMIT 10;

-- ============================================
-- PUBLIC DATASETS - GITHUB ARCHIVE
-- ============================================

-- Most active repositories
SELECT
    repo.name as repository,
    COUNT(*) as events
FROM `githubarchive.day.20240101`
GROUP BY repository
ORDER BY events DESC
LIMIT 10;

-- Programming language popularity
SELECT
    JSON_EXTRACT_SCALAR(payload, '$.pull_request.base.repo.language') as language,
    COUNT(*) as pr_count
FROM `githubarchive.month.202401`
WHERE type = 'PullRequestEvent'
    AND JSON_EXTRACT_SCALAR(payload, '$.pull_request.base.repo.language') IS NOT NULL
GROUP BY language
ORDER BY pr_count DESC
LIMIT 10;

-- ============================================
-- PUBLIC DATASETS - STACK OVERFLOW
-- ============================================

-- Most popular tags
SELECT
    tag_name,
    COUNT(*) as question_count
FROM `bigquery-public-data.stackoverflow.posts_questions`,
    UNNEST(SPLIT(tags, '|')) as tag_name
WHERE creation_date >= '2024-01-01'
GROUP BY tag_name
ORDER BY question_count DESC
LIMIT 20;

-- ============================================
-- ANALYTICS PATTERNS
-- ============================================

-- Time series with window functions
WITH daily_metrics AS (
    SELECT
        DATE(pickup_datetime) as date,
        COUNT(*) as daily_trips,
        SUM(fare_amount) as daily_revenue
    FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2020`
    WHERE DATE(pickup_datetime) BETWEEN '2020-01-01' AND '2020-01-31'
    GROUP BY date
)
SELECT
    date,
    daily_trips,
    daily_revenue,
    AVG(daily_trips) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as moving_avg_7_days
FROM daily_metrics
ORDER BY date;

-- ============================================
-- COST-OPTIMIZED QUERIES
-- ============================================

-- Use partitioning to reduce scan
SELECT
    COUNT(*) as trip_count
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2020`
WHERE DATE(pickup_datetime) = '2020-01-01';  -- Scans only one partition

-- Use APPROX functions for large datasets
SELECT
    APPROX_QUANTILES(fare_amount, 4)[OFFSET(2)] as median_fare,
    APPROX_TOP_COUNT(payment_type, 5) as top_payment_types
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2020`
WHERE DATE(pickup_datetime) BETWEEN '2020-01-01' AND '2020-01-31';
