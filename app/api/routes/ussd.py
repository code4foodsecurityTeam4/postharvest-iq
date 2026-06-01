from fastapi import APIRouter, Depends, Form
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services import ussd_service

router = APIRouter()

@router.post("/", response_class=PlainTextResponse)
async def ussd_callback(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(default=""),
    networkCode: str = Form(default=""),
    db: Session = Depends(get_db)
):
    response = ussd_service.handle_ussd_session(
        session_id=sessionId,
        phone_number=phoneNumber,
        text=text,
        db=db
    )
    return response