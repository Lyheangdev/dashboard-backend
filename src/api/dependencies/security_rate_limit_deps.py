from fastapi import Depends

from src.domain.utils.security.rate_limit_helper import RateLimiter

global_rate_limter = RateLimiter(request_limit=60, time_window_seconds=60)
GlobalRateLimiterDeps = Depends(global_rate_limter)
