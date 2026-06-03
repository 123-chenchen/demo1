from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_current_user_optional, get_db
from app.crud import CrudConflictError, chat_session_crud, document_content_crud, document_crud, notebook_crud
from app.db.models import User
from app.schemas import (
    AuthMeRead,
    ChatSessionCreate,
    ChatSessionRead,
    ChatSessionUpdate,
    ChatbotAskRequest,
    ChatbotAskResponse,
    DocumentContentRead,
    DocumentRead,
    DocumentUpdate,
    ForgotPasswordRequest,
    ForgotPasswordVerifyRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    NotebookCreate,
    NotebookRead,
    NotebookUpdate,
    OTPDeliveryResponse,
    RegisterRequest,
    RegisterVerifyRequest,
    RegisterVerifyResponse,
)
from app.services.auth import (
    AuthAuthenticationError,
    AuthConflictError,
    AuthDeliveryError,
    AuthForbiddenError,
    AuthNotFoundError,
    AuthValidationError,
    auth_service,
)
from app.services.documents import (
    DocumentUploadConflictError,
    DocumentUploadStorageError,
    DocumentUploadValidationError,
    document_upload_service,
)
from app.services.retrieval.ingestion import document_ingest_service

auth_router = APIRouter(prefix="/auth", tags=["auth"])
notebooks_router = APIRouter(prefix="/notebooks", tags=["notebooks"])
document_upload_router = APIRouter(prefix="/documents", tags=["documents"])
documents_router = APIRouter(prefix="/documents", tags=["documents"])
document_contents_router = APIRouter(prefix="/document-contents", tags=["document-contents"])
chat_sessions_router = APIRouter(prefix="/chat-sessions", tags=["chat-sessions"])
chatbot_router = APIRouter(prefix="/chatbot", tags=["chatbot"])


def _raise_auth_database_error(exc: SQLAlchemyError) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authentication database is not available.",
    ) from exc


@auth_router.get("/me", response_model=AuthMeRead, response_model_by_alias=False)
def get_authenticated_user(
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    return {
        "email": current_user.email,
        "name": auth_service.build_name_from_email(current_user.email),
    }


@auth_router.post("/register/request", response_model=OTPDeliveryResponse, response_model_by_alias=False)
def request_registration_otp(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return auth_service.request_register(
            db,
            email=payload.email,
            password=payload.password,
        )
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthDeliveryError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        _raise_auth_database_error(exc)


@auth_router.post(
    "/register/verify",
    response_model=RegisterVerifyResponse,
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
)
def verify_registration_otp(
    payload: RegisterVerifyRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return auth_service.verify_register(
            db,
            email=payload.email,
            otp=payload.otp,
        )
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        _raise_auth_database_error(exc)


@auth_router.post("/login", response_model=LoginResponse, response_model_by_alias=False)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return auth_service.login(
            db,
            email=payload.email,
            password=payload.password,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except AuthAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        _raise_auth_database_error(exc)


@auth_router.post("/forgot-password/request", response_model=OTPDeliveryResponse, response_model_by_alias=False)
def request_forgot_password_otp(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return auth_service.request_forgot_password(
            db,
            email=payload.email,
        )
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthDeliveryError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        _raise_auth_database_error(exc)


@auth_router.post("/forgot-password/verify", response_model=MessageResponse, response_model_by_alias=False)
def verify_forgot_password_otp(
    payload: ForgotPasswordVerifyRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return auth_service.verify_forgot_password(
            db,
            email=payload.email,
            otp=payload.otp,
            new_password=payload.new_password,
        )
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        _raise_auth_database_error(exc)


@notebooks_router.get("/", response_model=list[NotebookRead], response_model_by_alias=False)
def list_notebooks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[object]:
    return notebook_crud.list_for_user(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )


@notebooks_router.post(
    "/",
    response_model=NotebookRead,
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
)
def create_notebook(
    payload: NotebookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    try:
        return notebook_crud.create_for_user(
            db,
            user_id=current_user.id,
            obj_in=payload,
        )
    except CrudConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@notebooks_router.get("/{item_id}", response_model=NotebookRead, response_model_by_alias=False)
def get_notebook(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    notebook = notebook_crud.get_for_user(db, obj_id=item_id, user_id=current_user.id)
    if notebook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notebook not found.")
    return notebook


@notebooks_router.patch("/{item_id}", response_model=NotebookRead, response_model_by_alias=False)
def update_notebook(
    item_id: UUID,
    payload: NotebookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    notebook = notebook_crud.get_for_user(db, obj_id=item_id, user_id=current_user.id)
    if notebook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notebook not found.")
    try:
        return notebook_crud.update(db, db_obj=notebook, obj_in=payload)
    except CrudConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def _resolve_selected_notebook_id(
    db: Session,
    *,
    current_user: User | None,
    notebook_id: UUID | None,
) -> UUID | None:
    if current_user is None:
        return None
    try:
        notebook = auth_service.resolve_user_notebook(
            db,
            user=current_user,
            notebook_id=notebook_id,
        )
    except AuthNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return notebook.id


@documents_router.get("/", response_model=list[DocumentRead], response_model_by_alias=False)
def list_documents(
    notebook_id: UUID | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> list[object]:
    if current_user is None:
        return document_crud.list_for_scope(
            db,
            notebook_id=None,
            skip=skip,
            limit=limit,
        )

    return document_crud.list_for_user(
        db,
        user_id=current_user.id,
        notebook_id=_resolve_selected_notebook_id(
            db,
            current_user=current_user,
            notebook_id=notebook_id,
        ),
        skip=skip,
        limit=limit,
    )


@documents_router.get("/{item_id}", response_model=DocumentRead, response_model_by_alias=False)
def get_document(
    item_id: UUID,
    notebook_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> object:
    if current_user is None:
        document = document_crud.get_for_scope(
            db,
            obj_id=item_id,
            notebook_id=None,
        )
    else:
        document = document_crud.get_for_user(
            db,
            obj_id=item_id,
            user_id=current_user.id,
            notebook_id=notebook_id,
        )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found.")
    return document


@documents_router.patch("/{item_id}", response_model=DocumentRead, response_model_by_alias=False)
def update_document(
    item_id: UUID,
    payload: DocumentUpdate,
    notebook_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    document = document_crud.get_for_user(
        db,
        obj_id=item_id,
        user_id=current_user.id,
        notebook_id=notebook_id,
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found.")
    try:
        return document_crud.update(db, db_obj=document, obj_in=payload)
    except CrudConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@documents_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    item_id: UUID,
    notebook_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    document = document_crud.get_for_user(
        db,
        obj_id=item_id,
        user_id=current_user.id,
        notebook_id=notebook_id,
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found.")
    try:
        db.delete(document)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not delete Document because of a database constraint.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@document_upload_router.post(
    "/upload",
    response_model=DocumentRead,
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
)
def upload_document_pdf(
    file: UploadFile = File(...),
    notebook_id: UUID | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> DocumentRead:
    try:
        resolved_notebook_id = _resolve_selected_notebook_id(
            db,
            current_user=current_user,
            notebook_id=notebook_id,
        )
        return document_upload_service.upload_pdf(
            db,
            upload_file=file,
            notebook_id=resolved_notebook_id,
        )
    except DocumentUploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DocumentUploadConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DocumentUploadStorageError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@document_upload_router.post(
    "/{document_id}/ingest",
    response_model=DocumentRead,
    response_model_by_alias=False,
)
def ingest_document(
    document_id: UUID,
    notebook_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> DocumentRead:
    if current_user is None:
        document = document_crud.get_for_scope(
            db,
            obj_id=document_id,
            notebook_id=None,
        )
    else:
        document = document_crud.get_for_user(
            db,
            obj_id=document_id,
            user_id=current_user.id,
            notebook_id=notebook_id,
        )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found.")
    return document_ingest_service.ingest_document(db, document=document)


@document_contents_router.get("/", response_model=list[DocumentContentRead], response_model_by_alias=False)
def list_document_contents(
    notebook_id: UUID | None = Query(default=None),
    document_id: UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> list[object]:
    if current_user is None:
        return document_content_crud.list_for_scope(
            db,
            notebook_id=None,
            document_id=document_id,
            skip=skip,
            limit=limit,
        )

    return document_content_crud.list_for_user(
        db,
        user_id=current_user.id,
        notebook_id=_resolve_selected_notebook_id(
            db,
            current_user=current_user,
            notebook_id=notebook_id,
        ),
        document_id=document_id,
        skip=skip,
        limit=limit,
    )


@document_contents_router.get("/{item_id}", response_model=DocumentContentRead, response_model_by_alias=False)
def get_document_content(
    item_id: UUID,
    notebook_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> object:
    if current_user is None:
        content = document_content_crud.get_for_scope(
            db,
            obj_id=item_id,
            notebook_id=None,
        )
    else:
        content = document_content_crud.get_for_user(
            db,
            obj_id=item_id,
            user_id=current_user.id,
            notebook_id=notebook_id,
        )
    if content is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document content not found.")
    return content


@chat_sessions_router.get("/", response_model=list[ChatSessionRead], response_model_by_alias=False)
def list_chat_sessions(
    notebook_id: UUID | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[object]:
    try:
        selected_notebook = auth_service.resolve_user_notebook(
            db,
            user=current_user,
            notebook_id=notebook_id,
        )
    except AuthNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return chat_session_crud.list_for_user(
        db,
        user_id=current_user.id,
        notebook_id=selected_notebook.id,
        skip=skip,
        limit=limit,
    )


@chat_sessions_router.post(
    "/",
    response_model=ChatSessionRead,
    response_model_by_alias=False,
    status_code=status.HTTP_201_CREATED,
)
def create_chat_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    try:
        selected_notebook = auth_service.resolve_user_notebook(
            db,
            user=current_user,
            notebook_id=payload.notebook_id,
        )
        return chat_session_crud.create_for_notebook(
            db,
            notebook_id=selected_notebook.id,
            obj_in=payload,
        )
    except AuthNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CrudConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@chat_sessions_router.get("/{item_id}", response_model=ChatSessionRead, response_model_by_alias=False)
def get_chat_session(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    db_obj = chat_session_crud.get_for_user(db, obj_id=item_id, user_id=current_user.id)
    if db_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="chat session not found.",
        )
    return db_obj


@chat_sessions_router.patch("/{item_id}", response_model=ChatSessionRead, response_model_by_alias=False)
def update_chat_session(
    item_id: UUID,
    payload: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> object:
    db_obj = chat_session_crud.get_for_user(db, obj_id=item_id, user_id=current_user.id)
    if db_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="chat session not found.",
        )
    try:
        return chat_session_crud.update_for_notebook(
            db,
            db_obj=db_obj,
            obj_in=payload,
        )
    except CrudConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@chat_sessions_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    db_obj = chat_session_crud.get_for_user(db, obj_id=item_id, user_id=current_user.id)
    if db_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="chat session not found.",
        )
    try:
        chat_session_crud.delete(db, obj_id=item_id)
    except CrudConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@chatbot_router.post("/ask", response_model=ChatbotAskResponse, response_model_by_alias=False)
def ask_chatbot(
    payload: ChatbotAskRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, object]:
    from app.services.chatbot.service import (
        ChatbotServiceError,
        ChatbotServicePermissionError,
        chatbot_service,
    )

    try:
        return chatbot_service.ask(db, request=payload, current_user=current_user)
    except ChatbotServicePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ChatbotServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
