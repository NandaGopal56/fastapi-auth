import json
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from typing import Callable
from session.db_adapter import SessionStore

app = FastAPI()

@app.get("/")
def home(request: Request):
    request.state.session.save()
    return str(request.__dict__)

SESSION_KEY_NAME = 'sessionID'
SESSION_SAVE_EVERY_REQUEST = True

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
    
    if hasattr(request.state, 'session'):
        response.session = request.state.session
  
    try:
        accessed = response.session.accessed
        modified = response.session.modified
        empty = response.session.is_empty()
        
        print(response.session.__dict__)
    except AttributeError:
        raise AttributeError
        # we should return response here. for develomnet i am raiseing exception here
    
    if SESSION_KEY_NAME in request.cookies and empty:
        response.delete_cookie(SESSION_KEY_NAME)

    else:
        if accessed:
            pass
        if (modified or SESSION_SAVE_EVERY_REQUEST) and not empty:
            pass

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
