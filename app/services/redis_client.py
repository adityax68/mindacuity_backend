"""
Redis Client Service with Connection Pooling
Provides centralized Redis access for caching and state management
"""

import redis
import json
import logging
from typing import Optional, Any, List, Dict
from app.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Singleton Redis client with connection pooling
    """
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance
    
    def _initialize_pool(self):
        """Initialize Redis connection pool"""
        try:
            # Build connection pool kwargs
            pool_kwargs = {
                "host": settings.redis_host,
                "port": settings.redis_port,
                "db": settings.redis_db,
                "decode_responses": True,
                "max_connections": 50,
                "socket_timeout": 5,
                "socket_connect_timeout": 5,
                "retry_on_timeout": True
            }
            
            # Add password if provided
            if settings.redis_password:
                pool_kwargs["password"] = settings.redis_password
            
            # Handle SSL configuration (for redis-py 5.x compatibility)
            if settings.redis_ssl:
                pool_kwargs["connection_class"] = redis.SSLConnection
            
            self._pool = redis.ConnectionPool(**pool_kwargs)
            
            # Test connection
            client = redis.Redis(connection_pool=self._pool)
            client.ping()
            
            logger.info(f"Redis connection pool initialized successfully: {settings.redis_host}:{settings.redis_port}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection pool: {e}")
            raise
    
    def get_client(self) -> redis.Redis:
        """Get Redis client from pool"""
        return redis.Redis(connection_pool=self._pool)
    
    # ==================== STRING OPERATIONS ====================
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        Set key-value pair with optional expiry
        
        Args:
            key: Redis key
            value: Value (will be JSON serialized if dict/list)
            ex: Expiry time in seconds
        
        Returns:
            True if successful, False otherwise
        """
        try:
            client = self.get_client()
            
            # Serialize complex types
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            client.set(key, value, ex=ex)
            return True
            
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    def get(self, key: str, deserialize: bool = True) -> Optional[Any]:
        """
        Get value by key
        
        Args:
            key: Redis key
            deserialize: Whether to try JSON deserialization
        
        Returns:
            Value if found, None otherwise
        """
        try:
            client = self.get_client()
            value = client.get(key)
            
            if value is None:
                return None
            
            # Try to deserialize JSON
            if deserialize:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            
            return value
            
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    def delete(self, *keys: str) -> int:
        """Delete one or more keys"""
        try:
            client = self.get_client()
            return client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return 0
    
    def exists(self, *keys: str) -> int:
        """Check if keys exist"""
        try:
            client = self.get_client()
            return client.exists(*keys)
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return 0
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiry on key"""
        try:
            client = self.get_client()
            return client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
    
    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment key by amount"""
        try:
            client = self.get_client()
            return client.incr(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return None
    
    # ==================== LIST OPERATIONS ====================
    
    def lpush(self, key: str, *values: Any) -> Optional[int]:
        """Push values to the left (head) of list"""
        try:
            client = self.get_client()
            
            # Serialize complex types
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value))
                else:
                    serialized_values.append(value)
            
            return client.lpush(key, *serialized_values)
            
        except Exception as e:
            logger.error(f"Redis LPUSH error for key {key}: {e}")
            return None
    
    def rpush(self, key: str, *values: Any) -> Optional[int]:
        """Push values to the right (tail) of list"""
        try:
            client = self.get_client()
            
            # Serialize complex types
            serialized_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    serialized_values.append(json.dumps(value))
                else:
                    serialized_values.append(value)
            
            return client.rpush(key, *serialized_values)
            
        except Exception as e:
            logger.error(f"Redis RPUSH error for key {key}: {e}")
            return None
    
    def lrange(self, key: str, start: int, end: int, deserialize: bool = True) -> List[Any]:
        """Get range of elements from list"""
        try:
            client = self.get_client()
            values = client.lrange(key, start, end)
            
            if not deserialize:
                return values
            
            # Try to deserialize each value
            result = []
            for value in values:
                try:
                    result.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    result.append(value)
            
            return result
            
        except Exception as e:
            logger.error(f"Redis LRANGE error for key {key}: {e}")
            return []
    
    def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim list to specified range"""
        try:
            client = self.get_client()
            client.ltrim(key, start, end)
            return True
        except Exception as e:
            logger.error(f"Redis LTRIM error for key {key}: {e}")
            return False
    
    def llen(self, key: str) -> int:
        """Get length of list"""
        try:
            client = self.get_client()
            return client.llen(key)
        except Exception as e:
            logger.error(f"Redis LLEN error for key {key}: {e}")
            return 0
    
    # ==================== SET OPERATIONS ====================
    
    def sadd(self, key: str, *members: Any) -> Optional[int]:
        """Add members to set"""
        try:
            client = self.get_client()
            
            # Serialize complex types
            serialized_members = []
            for member in members:
                if isinstance(member, (dict, list)):
                    serialized_members.append(json.dumps(member))
                else:
                    serialized_members.append(str(member))
            
            return client.sadd(key, *serialized_members)
            
        except Exception as e:
            logger.error(f"Redis SADD error for key {key}: {e}")
            return None
    
    def smembers(self, key: str, deserialize: bool = False) -> set:
        """Get all members of set"""
        try:
            client = self.get_client()
            members = client.smembers(key)
            
            if not deserialize:
                return members
            
            # Try to deserialize
            result = set()
            for member in members:
                try:
                    result.add(json.loads(member))
                except (json.JSONDecodeError, TypeError):
                    result.add(member)
            
            return result
            
        except Exception as e:
            logger.error(f"Redis SMEMBERS error for key {key}: {e}")
            return set()
    
    def scard(self, key: str) -> int:
        """Get cardinality (size) of set"""
        try:
            client = self.get_client()
            return client.scard(key)
        except Exception as e:
            logger.error(f"Redis SCARD error for key {key}: {e}")
            return 0
    
    def sismember(self, key: str, member: Any) -> bool:
        """Check if member exists in set"""
        try:
            client = self.get_client()
            
            if isinstance(member, (dict, list)):
                member = json.dumps(member)
            
            return client.sismember(key, str(member))
            
        except Exception as e:
            logger.error(f"Redis SISMEMBER error for key {key}: {e}")
            return False
    
    # ==================== HASH OPERATIONS ====================
    
    def hset(self, key: str, field: str, value: Any) -> bool:
        """Set hash field"""
        try:
            client = self.get_client()
            
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            client.hset(key, field, value)
            return True
            
        except Exception as e:
            logger.error(f"Redis HSET error for key {key}, field {field}: {e}")
            return False
    
    def hget(self, key: str, field: str, deserialize: bool = True) -> Optional[Any]:
        """Get hash field value"""
        try:
            client = self.get_client()
            value = client.hget(key, field)
            
            if value is None:
                return None
            
            if deserialize:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            
            return value
            
        except Exception as e:
            logger.error(f"Redis HGET error for key {key}, field {field}: {e}")
            return None
    
    def hgetall(self, key: str, deserialize: bool = True) -> Dict[str, Any]:
        """Get all hash fields and values"""
        try:
            client = self.get_client()
            data = client.hgetall(key)
            
            if not deserialize:
                return data
            
            # Try to deserialize values
            result = {}
            for field, value in data.items():
                try:
                    result[field] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[field] = value
            
            return result
            
        except Exception as e:
            logger.error(f"Redis HGETALL error for key {key}: {e}")
            return {}
    
    # ==================== UTILITY OPERATIONS ====================
    
    def ping(self) -> bool:
        """Check if Redis is available"""
        try:
            client = self.get_client()
            return client.ping()
        except Exception as e:
            logger.error(f"Redis PING error: {e}")
            return False
    
    def flushdb(self) -> bool:
        """Flush current database (use with caution!)"""
        try:
            client = self.get_client()
            client.flushdb()
            logger.warning("Redis database flushed")
            return True
        except Exception as e:
            logger.error(f"Redis FLUSHDB error: {e}")
            return False


# Global Redis client instance
redis_client = RedisClient()

