from serverless_api import app

# This is the entry point for Vercel serverless function
def handler(request, context):
    """Vercel serverless function handler"""
    return app(request, context) 