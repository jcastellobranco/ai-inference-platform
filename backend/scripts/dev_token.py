"""Generate short-lived local JWTs. Never use in production."""
import argparse
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID
import jwt

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--tenant",required=True)
    parser.add_argument("--subject",default="developer")
    args=parser.parse_args()
    tenant=str(UUID(args.tenant))
    secret=os.environ["JWT_SECRET"]
    if len(secret)<32:
        raise ValueError("JWT_SECRET must be at least 32 characters")
    claims={"sub":args.subject,"tenant_id":tenant,"iss":"portfolio-dev","aud":"ai-platform","exp":datetime.now(timezone.utc)+timedelta(minutes=30)}
    print(jwt.encode(claims,secret,algorithm="HS256"))

if __name__=="__main__":
    main()
