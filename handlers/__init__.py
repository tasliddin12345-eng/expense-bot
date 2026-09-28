from . import start, reports, settings, transaction

# IMPORTANT: order matters. Routers with specific commands (start, reports,
# settings) must be registered before `transaction`, because `transaction`
# contains a catch-all quick-entry handler that matches any text containing
# a digit. If it were checked first, it could swallow commands like
# "/limit 500000".
routers = [
    start.router,
    reports.router,
    settings.router,
    transaction.router,
]
