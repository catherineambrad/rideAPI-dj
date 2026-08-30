# Ride API

Admin CRUD for users, rides, and ride events. The ride list is paginated and can filter by status or rider email, include rider/driver plus events from the last 24 hours, and sort by pickup time or distance.

## Stack

- Python 3.12
- Django 5.2
- Django REST Framework 3.16
- PostgreSQL 17

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set the Postgres user/password to match your local server. Django reads that file automatically. Then:

```bash
python run.py migrate
python run.py createsuperuser
python run.py runserver
```

The API is at `http://127.0.0.1:8000/api/`. The browsable API accepts the superuser created above.

## Endpoints

All endpoints require an authenticated user with `role=admin`. Session and HTTP Basic auth are enabled.


| Method                  | Endpoint                 | Purpose                           |
| ----------------------- | ------------------------ | --------------------------------- |
| GET, POST               | `/api/users/`            | List or create users              |
| GET, PUT, PATCH, DELETE | `/api/users/{id}/`       | Retrieve or modify one user       |
| GET, POST               | `/api/rides/`            | List or create rides              |
| GET, PUT, PATCH, DELETE | `/api/rides/{id}/`       | Retrieve or modify one ride       |
| GET, POST               | `/api/ride-events/`      | List or create ride events        |
| GET, PUT, PATCH, DELETE | `/api/ride-events/{id}/` | Retrieve or modify one ride event |


```bash
curl -u admin@example.com:your-password \
  "http://127.0.0.1:8000/api/rides/?status=pickup&rider_email=rider@example.com&page=1&page_size=20&ordering=pickup_time"
```



### Ride filters and ordering


| Parameter          | Accepted values                                        | Notes                           |
| ------------------ | ------------------------------------------------------ | ------------------------------- |
| `status`           | `en-route`, `pickup`, `dropoff`                        | Exact status match              |
| `rider_email`      | Valid email string                                     | Case-insensitive exact match    |
| `ordering`         | `pickup_time`, `-pickup_time`, `distance`, `-distance` | Minus means descending          |
| `pickup_latitude`  | -90 through 90                                         | Required with distance ordering |
| `pickup_longitude` | -180 through 180                                       | Required with distance ordering |
| `page`             | Positive integer                                       | Page number                     |
| `page_size`        | 1 through 100                                          | Defaults to 20                  |


```bash
curl -u admin@example.com:your-password \
  "http://127.0.0.1:8000/api/rides/?ordering=distance&pickup_latitude=34.0522&pickup_longitude=-118.2437"
```

Distance results include `distance_km`.

The list uses `select_related` for rider and driver, and a filtered `Prefetch` for events from the last 24 hours. Distance is calculated in SQL so sorting and pagination stay in the database.

## *SQL report

First pickup event per ride, then the first dropoff after that pickup. Counts trips longer than one hour, by pickup month and driver.

```sql
WITH pickup_events AS (
    SELECT
        re.id_ride,
        MIN(re.created_at) AS pickup_at
    FROM ride_event AS re
    WHERE re.description = 'Status changed to pickup'
    GROUP BY re.id_ride
),
trip_times AS (
    SELECT
        r.id_ride,
        r.id_driver,
        p.pickup_at,
        MIN(dropoff.created_at) AS dropoff_at
    FROM pickup_events AS p
    JOIN ride AS r
      ON r.id_ride = p.id_ride
    JOIN ride_event AS dropoff
      ON dropoff.id_ride = r.id_ride
     AND dropoff.description = 'Status changed to dropoff'
     AND dropoff.created_at > p.pickup_at
    GROUP BY r.id_ride, r.id_driver, p.pickup_at
)
SELECT
    TO_CHAR(DATE_TRUNC('month', t.pickup_at), 'YYYY-MM') AS month,
    CONCAT_WS(' ', u.first_name, LEFT(u.last_name, 1)) AS driver,
    COUNT(*) AS "count_of_trips_over_1_hr"
FROM trip_times AS t
JOIN "user" AS u
  ON u.id_user = t.id_driver
WHERE t.dropoff_at - t.pickup_at > INTERVAL '1 hour'
GROUP BY DATE_TRUNC('month', t.pickup_at), u.id_user, u.first_name, u.last_name
ORDER BY DATE_TRUNC('month', t.pickup_at), driver;
```

