# Database Schema

Tai lieu nay mo ta schema PostgreSQL hien tai cua backend PDF Chatbot.

## Muc tieu

Database duoc chia thanh 4 nhom chinh:

- Authentication: `users`, `refresh_tokens`
- Document ingestion: `documents`, `document_contents`, `document_chunks`
- Chat history: `chat_sessions`, `chat_messages`
- Retrieval trace: `message_sources`

## Enum

### `document_status`

- `pending`: tai lieu da duoc tao record nhung chua xu ly xong
- `processed`: tai lieu da extract text, chunk va san sang retrieval
- `failed`: pipeline xu ly tai lieu bi loi

### `message_role`

- `user`: cau hoi/yeu cau tu nguoi dung
- `assistant`: cau tra loi tu bot
- `system`: message he thong, instruction, hoac hidden context

## Quan he tong quan

```text
users 1---n refresh_tokens
users 1---n chat_sessions

documents 1---1 document_contents
documents 1---n document_chunks

chat_sessions 1---n chat_messages
chat_messages 1---n message_sources
document_chunks 1---n message_sources
```

## Bang `users`

Luu tai khoan dang nhap cua he thong.

| Attribute | Type | Nullable | Rang buoc | Y nghia |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Dinh danh user |
| `email` | `varchar(255)` | No | Unique | Email dang nhap chinh |
| `username` | `varchar(50)` | Yes | Unique | Username hien thi hoac login phu |
| `password_hash` | `varchar(255)` | No |  | Mat khau da hash, khong luu plain text |
| `full_name` | `varchar(255)` | Yes |  | Ho ten nguoi dung |
| `is_active` | `boolean` | No | default `true` | User con duoc phep su dung he thong |
| `is_superuser` | `boolean` | No | default `false` | Quyen admin/noi bo |
| `last_login_at` | `timestamptz` | Yes |  | Thoi diem login thanh cong gan nhat |
| `metadata` | `jsonb` | No | default `{}` | Du lieu mo rong cho profile/quyen/cai dat |
| `created_at` | `timestamptz` | No | default `now()` | Thoi diem tao record |
| `updated_at` | `timestamptz` | No | default `now()` | Thoi diem cap nhat record |

## Bang `refresh_tokens`

Luu refresh token de quan ly session dang nhap lau dai.

| Attribute | Type | Nullable | Rang buoc | Y nghia |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Dinh danh record refresh token |
| `user_id` | `uuid` | No | FK -> `users.id`, index, on delete cascade | Token thuoc ve user nao |
| `token_jti` | `varchar(255)` | No | Unique | JWT ID hoac ma dinh danh duy nhat cua token |
| `token_hash` | `varchar(255)` | No |  | Ban hash cua refresh token de tranh luu token goc |
| `expires_at` | `timestamptz` | No |  | Thoi diem het han |
| `revoked_at` | `timestamptz` | Yes |  | Thoi diem token bi revoke |
| `last_used_at` | `timestamptz` | Yes |  | Thoi diem token duoc su dung gan nhat |
| `user_agent` | `varchar(512)` | Yes |  | Thong tin trinh duyet/thiet bi |
| `ip_address` | `varchar(64)` | Yes |  | IP dang nhap hoac refresh |
| `created_at` | `timestamptz` | No | default `now()` | Thoi diem tao token |

## Bang `documents`

Moi file tai len la mot record.

| Attribute | Type | Nullable | Rang buoc | Y nghia |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Dinh danh tai lieu |
| `storage_key` | `varchar(512)` | No | Unique | Duong dan/object key trong storage |
| `original_file_name` | `varchar(255)` | No |  | Ten file goc nguoi dung upload |
| `mime_type` | `varchar(100)` | No | default `application/pdf` | Loai file |
| `file_size_bytes` | `bigint` | Yes |  | Kich thuoc file |
| `total_pages` | `integer` | Yes |  | So trang cua tai lieu |
| `total_chunks` | `integer` | No | default `0` | Tong so chunks sau khi chunk |
| `status` | `document_status` | No | default `pending` | Trang thai pipeline xu ly |
| `metadata` | `jsonb` | No | default `{}` | OCR info, source info, tags, custom flags |
| `created_at` | `timestamptz` | No | default `now()` | Thoi diem tao record |
| `updated_at` | `timestamptz` | No | default `now()` | Thoi diem cap nhat record |

## Bang `document_contents`

Luu text tho da extract tu tai lieu. Bang nay la lop trung gian giua file goc va chunks.

| Attribute | Type | Nullable | Rang buoc | Y nghia |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Dinh danh noi dung extract |
| `document_id` | `uuid` | No | FK -> `documents.id`, Unique, on delete cascade | Moi document co toi da 1 record content |
| `raw_text` | `text` | No |  | Toan bo noi dung text sau khi extract/OCR |
| `character_count` | `integer` | Yes |  | So ky tu cua `raw_text` |
| `content_hash` | `varchar(64)` | Yes |  | Hash cua text extract de detect thay doi |
| `extractor_name` | `varchar(255)` | Yes |  | Ten tool/model extract, vi du `pypdf`, `ocrmypdf` |
| `metadata` | `jsonb` | No | default `{}` | OCR confidence, layout info, language, warnings |
| `created_at` | `timestamptz` | No | default `now()` | Thoi diem tao record |
| `updated_at` | `timestamptz` | No | default `now()` | Thoi diem cap nhat record |

## Bang `document_chunks`

Luu cac doan text nho duoc sinh ra tu `document_contents` de embedding va retrieval.

| Attribute | Type | Nullable | Rang buoc | Y nghia |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Dinh danh chunk |
| `document_id` | `uuid` | No | FK -> `documents.id`, index, on delete cascade | Chunk thuoc ve tai lieu nao |
| `chunk_index` | `integer` | No | Unique theo cap `document_id + chunk_index`, check `>= 0` | Thu tu chunk trong document |
| `page_from` | `integer` | Yes |  | Trang bat dau cua chunk |
| `page_to` | `integer` | Yes |  | Trang ket thuc cua chunk |
| `content` | `text` | No |  | Noi dung chunk duoc dung de embed/search |
| `token_count` | `integer` | Yes |  | So token cua chunk |
| `character_count` | `integer` | Yes |  | So ky tu cua chunk |
| `qdrant_point_id` | `varchar(128)` | Yes | Unique | ID point trong Qdrant de map sang vector |
| `embedding_model` | `varchar(255)` | Yes |  | Model da dung de tao embedding |
| `metadata` | `jsonb` | No | default `{}` | Chunk overlap, section title, heading, score phu |
| `created_at` | `timestamptz` | No | default `now()` | Thoi diem tao chunk |

## Bang `chat_sessions`

Dai dien cho mot cuoc hoi thoai.

| Attribute | Type | Nullable | Rang buoc | Y nghia |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Dinh danh session |
| `user_id` | `uuid` | Yes | FK -> `users.id`, index, on delete set null | Session co the gan voi user da dang nhap |
| `title` | `varchar(255)` | Yes |  | Tieu de session de hien thi UI |
| `metadata` | `jsonb` | No | default `{}` | Prompt preset, locale, filter retrieval, UI state |
| `created_at` | `timestamptz` | No | default `now()` | Thoi diem tao session |
| `updated_at` | `timestamptz` | No | default `now()` | Thoi diem cap nhat session |

## Bang `chat_messages`

Luu tung message trong session chat.

| Attribute | Type | Nullable | Rang buoc | Y nghia |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Dinh danh message |
| `session_id` | `uuid` | No | FK -> `chat_sessions.id`, index, on delete cascade | Message thuoc ve session nao |
| `reply_to_message_id` | `uuid` | Yes | Self FK -> `chat_messages.id`, index, on delete set null | Message dang reply cho message nao |
| `role` | `message_role` | No |  | Vai tro message: user/assistant/system |
| `content` | `text` | No |  | Noi dung text cua message |
| `model_name` | `varchar(255)` | Yes |  | Model da tao ra cau tra loi |
| `prompt_tokens` | `integer` | Yes |  | So token input |
| `completion_tokens` | `integer` | Yes |  | So token output |
| `total_tokens` | `integer` | Yes |  | Tong token su dung |
| `metadata` | `jsonb` | No | default `{}` | latency, temperature, trace id, generation config |
| `created_at` | `timestamptz` | No | default `now()` | Thoi diem tao message |

## Bang `message_sources`

Luu cac chunk da duoc su dung de tao mot cau tra loi. Bang nay giup trace retrieval.

| Attribute | Type | Nullable | Rang buoc | Y nghia |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Dinh danh source row |
| `message_id` | `uuid` | No | FK -> `chat_messages.id`, index, on delete cascade | Thuoc ve cau tra loi nao |
| `chunk_id` | `uuid` | No | FK -> `document_chunks.id`, index, on delete restrict | Chunk nao da duoc su dung |
| `source_rank` | `integer` | No | check `>= 1` | Thu hang chunk trong danh sach context |
| `score` | `float` | Yes |  | Similarity score hoac rerank score |
| `snippet` | `text` | Yes |  | Doan trich ngan duoc dua vao UI/debug |
| `created_at` | `timestamptz` | No | default `now()` | Thoi diem gan source vao message |

## Chu y thiet ke

- `metadata` duoc dat la `jsonb` o nhieu bang de mo rong schema ma khong phai migration ngay lap tuc.
- `document_contents` ton tai de co the re-chunk, re-embed hoac debug extract ma khong can doc lai PDF goc.
- `qdrant_point_id` chi luu map sang vector store, khong luu embedding trong PostgreSQL.
- `message_sources` la bang quan trong de explainability: bot tra loi dua tren nhung chunk nao.

## Thu tu insert du lieu khuyen nghi

1. Tao `users` neu co auth.
2. Tao `documents`.
3. Extract text va tao `document_contents`.
4. Chunk text va tao `document_chunks`.
5. Tao `chat_sessions`.
6. Tao `chat_messages`.
7. Ghi `message_sources` cho cac message `assistant`.
