"""Promote an existing CivicPulse account to administrator."""
import sys

from sqlalchemy import select

from app.database.connection import SessionLocal
from app.models.user import User


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m app.promote_admin <account-email>")
        raise SystemExit(2)
    email = sys.argv[1].strip().lower()
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            print("No CivicPulse account has that email. Create the account first, then promote it.")
            raise SystemExit(1)
        if user.role == "admin":
            print(f"{user.email} already has administrator access.")
            return
        confirm = input(f"Grant administrator access to {user.email}? Type 'yes' to continue: ")
        if confirm.strip().lower() != "yes":
            print("No changes made.")
            return
        user.role = "admin"
        db.commit()
        print(f"Administrator access granted to {user.email}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
