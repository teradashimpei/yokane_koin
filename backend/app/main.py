from fastapi import FastAPI

from app.errors import register_error_handlers
from app.routers import admin, customer_replies, health, staff_auth, staff_insights, staff_profile, staff_requests

app = FastAPI(title="yokane-koin(行員側)")
register_error_handlers(app)
for r in (health, staff_auth, staff_profile, staff_requests, staff_insights, customer_replies, admin):
    app.include_router(r.router)
