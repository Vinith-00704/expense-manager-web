import os; from dotenv import load_dotenv; load_dotenv()
from app import create_app
app = create_app()
with app.app_context():
    from app.services import dashboard_service
    import traceback
    tests = [
        ('savings_history', lambda: dashboard_service.get_savings_history(6, 6)),
        ('category_breakdown', lambda: dashboard_service.get_category_breakdown(6)),
        ('alerts', lambda: dashboard_service.get_alerts(6)),
        ('upcoming', lambda: dashboard_service.get_upcoming_expenses(6)),
    ]
    for label, fn in tests:
        try:
            r = fn()
            print(f"{label}: OK -> {r}")
        except Exception:
            print(f"\n{label}: FAILED")
            traceback.print_exc()
