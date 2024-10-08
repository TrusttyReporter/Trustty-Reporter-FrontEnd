import redis
import ssl

redis_url = "rediss://red-cruis6rqf0us73epeu10:TocPDg7slIXSAp82yFDiY4eHZYdP0T82@ohio-redis.render.com:6379"

try:
    r = redis.from_url(
        redis_url,
        ssl_cert_reqs=ssl.CERT_NONE  # Use the constant from ssl module
    )
    r.ping()
    print("Successfully connected to Redis")
except Exception as e:
    print(f"Failed to connect to Redis: {e}")