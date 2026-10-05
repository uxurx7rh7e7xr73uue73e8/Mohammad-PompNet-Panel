import os


def runtime_status():
    return {
        "platform": "Railway",

        "port": os.getenv(
            "PORT",
            ""
        ),

        "public_domain": os.getenv(
            "RAILWAY_PUBLIC_DOMAIN",
            ""
        ),

        "private_domain": os.getenv(
            "RAILWAY_PRIVATE_DOMAIN",
            ""
        ),

        "environment": os.getenv(
            "RAILWAY_ENVIRONMENT_NAME",
            ""
        ),

        "service": os.getenv(
            "RAILWAY_SERVICE_NAME",
            ""
        ),

        "deployment": os.getenv(
            "RAILWAY_DEPLOYMENT_ID",
            ""
        ),

        "project": os.getenv(
            "RAILWAY_PROJECT_ID",
            ""
        ),

        "status": "running"
    }
