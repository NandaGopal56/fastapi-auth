
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from typing import Callable
from session.db_adapter import SessionStore

app = FastAPI()

@app.get("/")
def home():
    return {
        'foo': 'bar'
    }

SESSION_KEY_NAME = 'sessionID'

# Middleware for adding custom header to requests
async def request_middleware_handler(request: Request, call_next: Callable) -> Response:
    session_key = request.cookies.get(SESSION_KEY_NAME)
    request.state.session = SessionStore(session_key)
    print(request.state.session.__dict__)
    # Proceed with the request handling
    response = await call_next(request)
    return response

# Middleware for adding custom header to responses
async def response_middleware_handler(request: Request, call_next: Callable) -> Response:
    # Execute the request and get the response
    response = await call_next(request)
    return response

# Apply middleware for requests
@app.middleware("http")
async def request_middleware(request: Request, call_next: Callable) -> Response:
    # Apply request headers middleware
    response = await request_middleware_handler(request, call_next)
    return response

# Apply middleware for responses
@app.middleware("http")
async def response_middleware(request: Request, call_next: Callable) -> Response:
    # Apply response headers middleware
    response = await response_middleware_handler(request, call_next)
    return response



if __name__ == '__main__':
    try:
        uvicorn.run("main:app", port=9000, reload=True)
    except KeyboardInterrupt:
        print('Server stopped by user')
    finally:
        pass
