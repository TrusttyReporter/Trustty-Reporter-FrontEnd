import redis
import ssl
import socket

redis_url = "rediss://red-cs825pq3esus73cp36ag:iyQbpNUzn5cgGHu85uu4YZpMBYB2EdXG@ohio-redis.render.com:6379"

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "Unable to determine IP"
    finally:
        s.close()

try:
    print(f"Attempting to connect from IP: {get_local_ip()}")
    r = redis.from_url(
        redis_url,
        ssl_cert_reqs=ssl.CERT_NONE
    )
    r.ping()
    print("Successfully connected to Redis")
except redis.exceptions.ConnectionError as e:
    print(f"Failed to connect to Redis: {e}")
    print("Please ensure your IP is in the Redis allowlist.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")