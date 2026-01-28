from pydantic import BaseModel, HttpUrl


class WebsiteKBRequest(BaseModel):
    url: HttpUrl


class WebsiteKBResponse(BaseModel):
    url: str
    total_text_length: int
    chunks_created: int
    rows_inserted: int