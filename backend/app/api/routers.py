from __future__ import annotations

from io import BytesIO
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user, get_current_user_optional, get_db
from app.crud import CrudConflictError, chat_session_crud, document_content_crud, document_crud, notebook_crud
from app.db.models import ChatMessage, ChatSession, Document, MessageSource, Notebook, User
from app.db.models.document import DocumentChunk
from app.schemas import (
    AuthMeRead,
    CitationRead,
    ChangePasswordRequest,
    ChatSessionCreate,
    ChatSessionDetailRead,
    ChatSessionRead,
    ChatSessionUpdate,
    ChatbotAskRequest,
    ChatbotAskResponse,
    ChatbotSuggestionsRequest,
    ChatbotSuggestionsResponse,
    DeleteAccountRequest,
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
    UserSettingsRead,
    UserSettingsUpdate,
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
from app.services.retrieval.vector_store import VectorStoreError, delete_points
from app.services.storage import StorageServiceError, delete_object, get_object_buffer, parse_storage_key

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
) -> dict[str, object]:
    return {
        "email": current_user.email,
        "name": auth_service.resolve_user_display_name(current_user),
        "settings": auth_service.get_user_settings(current_user),
    }


@auth_router.get("/settings", response_model=UserSettingsRead, response_model_by_alias=False)
def get_user_settings(
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    return auth_service.get_user_settings(current_user)


@auth_router.patch("/settings", response_model=UserSettingsRead, response_model_by_alias=False)
def update_user_settings(
    payload: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        return auth_service.update_user_settings(
            db,
            user=current_user,
            language=payload.language,
            theme=payload.theme,
        )
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        _raise_auth_database_error(exc)


@auth_router.post("/change-password", response_model=MessageResponse, response_model_by_alias=False)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        return auth_service.change_password(
            db,
            user=current_user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except AuthAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        _raise_auth_database_error(exc)


@auth_router.delete("/account", response_model=MessageResponse, response_model_by_alias=False)
def delete_account(
    payload: DeleteAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    try:
        return auth_service.delete_account(
            db,
            user=current_user,
            current_password=payload.current_password,
        )
    except AuthAuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        _raise_auth_database_error(exc)


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

# Hàm _resolve_selected_notebook_id sẽ được sử dụng trong các API có nhận tham số notebook_id để xác định xem notebook_id đó có hợp lệ và thuộc về người dùng hiện tại hay không. Nếu notebook_id không hợp lệ hoặc không thuộc về người dùng, nó sẽ ném ra lỗi HTTP 404 Not Found với thông điệp chi tiết. Nếu notebook_id hợp lệ, nó sẽ trả về UUID của notebook đó để các API khác có thể sử dụng để truy vấn dữ liệu liên quan đến notebook.
@notebooks_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notebook(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    notebook = notebook_crud.get_for_user(db, obj_id=item_id, user_id=current_user.id)
    if notebook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notebook not found.")

    documents = list(db.scalars(select(Document).where(Document.notebook_id == notebook.id)).all())
    cleanup_items: list[dict[str, object]] = []

    try:
        db.execute(delete(ChatSession).where(ChatSession.notebook_id == notebook.id))
        for document in documents:
            cleanup_items.append(_prepare_document_delete(db, document=document))
        db.delete(notebook)
        db.commit()

        if notebook_crud.get_default_for_user(db, user_id=current_user.id) is None:
            auth_service.ensure_user_default_notebook(db, user=current_user)
            db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not delete notebook.",
        ) from exc

    for cleanup_item in cleanup_items:
        _cleanup_deleted_document_resources(cleanup_item)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@documents_router.get("/{item_id}/file")
def get_document_file(
    item_id: UUID,
    notebook_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> StreamingResponse:
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

    try:
        bucket_name, object_name = parse_storage_key(document.storage_key)
        file_buffer = get_object_buffer(bucket_name, object_name)
    except StorageServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    filename = quote(document.original_file_name)
    return StreamingResponse(
        _iter_buffer(file_buffer),
        media_type=document.mime_type or "application/pdf",
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{filename}",
            "Cache-Control": "private, max-age=300",
        },
    )


@documents_router.get("/{item_id}/pdf")
def get_document_pdf(
    item_id: UUID,
    notebook_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> StreamingResponse:
    return get_document_file(
        item_id=item_id,
        notebook_id=notebook_id,
        db=db,
        current_user=current_user,
    )


@documents_router.get(
    "/{item_id}/citation/{chunk_id}",
    response_model=CitationRead,
    response_model_by_alias=False,
)
def get_document_citation(
    item_id: UUID,
    chunk_id: UUID,
    notebook_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, object]:
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

    chunk = db.scalar(
        select(DocumentChunk).where(
            DocumentChunk.id == chunk_id,
            DocumentChunk.document_id == document.id,
        )
    )
    if chunk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="citation not found.")

    metadata = dict(chunk.extra_metadata or {})
    return {
        "document_id": document.id,
        "document_name": _document_display_title(document),
        "page_number": chunk.page_from,
        "chunk_id": chunk.id,
        "chunk_index": chunk.chunk_index,
        "text": chunk.content,
        "quoted_text": metadata.get("quoted_text") or chunk.content,
        "bbox": metadata.get("bbox"),
        "page_width": metadata.get("page_width"),
        "page_height": metadata.get("page_height"),
    }


def _iter_buffer(file_buffer: BytesIO, chunk_size: int = 1024 * 1024):
    try:
        while True:
            chunk = file_buffer.read(chunk_size)
            if not chunk:
                break
            yield chunk
    finally:
        file_buffer.close()


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
        cleanup_item = _prepare_document_delete(db, document=document)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not delete Document because of a database constraint.",
        ) from exc

    _cleanup_deleted_document_resources(cleanup_item)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _prepare_document_delete(db: Session, *, document: Document) -> dict[str, object]:
    point_ids = [
        point_id
        for point_id in db.scalars(
            select(DocumentChunk.qdrant_point_id).where(
                DocumentChunk.document_id == document.id,
                DocumentChunk.qdrant_point_id.is_not(None),
            )
        )
        if point_id
    ]
    chunk_ids = select(DocumentChunk.id).where(DocumentChunk.document_id == document.id)
    db.execute(delete(MessageSource).where(MessageSource.chunk_id.in_(chunk_ids)))
    db.delete(document)
    return {
        "document_id": str(document.id),
        "storage_key": document.storage_key,
        "point_ids": point_ids,
    }


def _cleanup_deleted_document_resources(cleanup_item: dict[str, object]) -> None:
    point_ids = cleanup_item.get("point_ids") or []
    storage_key = str(cleanup_item.get("storage_key") or "")
    document_id = cleanup_item.get("document_id")

    if point_ids:
        try:
            delete_points([str(point_id) for point_id in point_ids])
        except VectorStoreError as exc:
            logger.warning("Could not delete vectors for document {}: {}", document_id, exc)

    try:
        bucket_name, object_name = parse_storage_key(storage_key)
        delete_object(bucket_name, object_name)
    except StorageServiceError as exc:
        logger.warning("Could not delete stored PDF for document {}: {}", document_id, exc)


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
        return document_upload_service.upload_pdf( # upload PDF sẽ bao gồm cả việc validate file, upload file lên MinIO và tạo record Document trong database, nên có thể sẽ mất nhiều thời gian hơn so với các API khác, cần cân nhắc về việc có nên xử lý upload file và tạo record Document thành 2 bước riêng biệt hay không để cải thiện trải nghiệm người dùng
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


def _serialize_chat_session_detail(session: ChatSession) -> dict[str, object]:
    return {
        "id": session.id,
        "notebook_id": session.notebook_id,
        "title": session.title,
        "metadata": session.extra_metadata,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "messages": [
            {
                "id": message.id,
                "session_id": message.session_id,
                "reply_to_message_id": message.reply_to_message_id,
                "role": message.role,
                "content": message.content,
                "model_name": message.model_name,
                "prompt_tokens": message.prompt_tokens,
                "completion_tokens": message.completion_tokens,
                "total_tokens": message.total_tokens,
                "metadata": message.extra_metadata,
                "created_at": message.created_at,
                "sources": [_serialize_history_source(source) for source in sorted(message.sources, key=lambda item: item.source_rank)],
            }
            for message in session.messages
        ],
    }


def _serialize_history_source(source: MessageSource) -> dict[str, object]:
    chunk = source.chunk
    document = chunk.document
    metadata = dict(chunk.extra_metadata or {})
    return {
        "chunk_id": chunk.id,
        "document_id": document.id,
        "document_name": _document_display_title(document),
        "original_file_name": document.original_file_name,
        "storage_key": document.storage_key,
        "content": chunk.content,
        "chunk_index": chunk.chunk_index,
        "page_number": chunk.page_from,
        "page_from": chunk.page_from,
        "page_to": chunk.page_to,
        "quoted_text": metadata.get("quoted_text") or source.snippet or chunk.content,
        "bbox": metadata.get("bbox"),
        "page_width": metadata.get("page_width"),
        "page_height": metadata.get("page_height"),
        "score": source.score,
        "source": "history",
        "metadata": metadata,
    }


def _document_display_title(document: object) -> str:
    metadata = dict(getattr(document, "extra_metadata", None) or {})
    for key in ("display_title", "title", "document_title", "pdf_title", "extracted_title", "subject", "topic"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    return getattr(document, "original_file_name", None) or "Referenced PDF"


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


@chat_sessions_router.get("/{item_id}", response_model=ChatSessionDetailRead, response_model_by_alias=False)
def get_chat_session(
    item_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    existing_session = chat_session_crud.get_for_user(
        db,
        obj_id=item_id,
        user_id=current_user.id,
    )
    if existing_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="chat session not found.",
        )

    db_obj = db.scalar(
        select(ChatSession)
        .join(Notebook)
        .options(
            selectinload(ChatSession.messages)
            .selectinload(ChatMessage.sources)
            .selectinload(MessageSource.chunk)
            .selectinload(DocumentChunk.document)
        )
        .where(
            ChatSession.id == item_id,
            Notebook.user_id == current_user.id,
        )
    )
    if db_obj is None:
        db_obj = existing_session
    return _serialize_chat_session_detail(db_obj)


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


@chatbot_router.post("/suggestions", response_model=ChatbotSuggestionsResponse, response_model_by_alias=False)
def suggest_chatbot_questions(
    payload: ChatbotSuggestionsRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, object]:
    from app.services.chatbot.service import (
        ChatbotServiceError,
        ChatbotServicePermissionError,
        chatbot_service,
    )

    try:
        return chatbot_service.suggest_questions(db, request=payload, current_user=current_user)
    except ChatbotServicePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ChatbotServiceError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
