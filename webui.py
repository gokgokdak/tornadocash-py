from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

import config


app      : FastAPI         = FastAPI()
templates: Jinja2Templates = Jinja2Templates(directory=os.path.join(config.WEBUI_ROOT, "templates"))


@app.get("/", response_class=HTMLResponse)
def root(req: Request):
    return templates.TemplateResponse("index.html", context={"request": req})
