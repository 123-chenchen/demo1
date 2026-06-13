# Database Schema

This document describes the current PostgreSQL schema for the PDF Chatbot backend.

## Purpose

The schema is organized into four main areas:

- Authentication and workspace: `users`, `notebooks`, `pending_registrations`, `email_otps`, `refresh_tokens`
- Document ingestion: `documents`, `document_contents`, `document_chunks`
- Chat history: `chat_sessions`, `chat_messages`
- Retrieval traceability: `message_sources`

## Enums

### `document_status`

- `pending`: the document record exists but processing has not completed
- `processed`: text extraction, chunking, and indexing completed successfully
- `failed`: document processing failed

### `message_role`

- `user`: a user question or request
- `assistant`: an assistant response
- `system`: a system message, instruction, or hidden context

## Relationship Overview

```text
users 1---n notebooks
users 1---n refresh_tokens
notebooks 1---n documents
notebooks 1---n chat_sessions

documents 1---1 document_contents
documents 1---n document_chunks

chat_sessions 1---n chat_messages
chat_messages 1---n message_sources
document_chunks 1---n message_sources
```

## Table: `users`

Stores application login accounts.

| Attribute | Type | Nullable | Constraint | Meaning |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | User identifier |
| `email` | `varchar(255)` | No | Unique | Primary login email |
| `password_hash` | `varchar(255)` | No |  | Hashed password; plain text passwords are not stored |
| `is_verified` | `boolean` | No | default `false` | Whether the email was verified by OTP |
| `is_active` | `boolean` | No | default `true` | Whether the user can use the system |
| `is_superuser` | `boolean` | No | default `false` | Internal administrator flag |
| `last_login_at` | `timestamptz` | Yes |  | Most recent successful login time |
| `metadata` | `jsonb` | No | default `{}` | Extension data for profile, permissions, or settings |
| `created_at` | `timestamptz` | No | default `now()` | Record creation time |
| `updated_at` | `timestamptz` | No | default `now()` | Record update time |

The display name is not stored as a separate column. The backend derives `name` from the email local part, for example `nguyen.van.a@gmail.com` becomes `Nguyen Van A`.

## Table: `notebooks`

Each user can own multiple notebooks. When a user is first created and verified, the backend creates one default notebook for compatibility with earlier flows.

| Attribute | Type | Nullable | Constraint | Meaning |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Notebook identifier |
| `user_id` | `uuid` | No | FK -> `users.id`, index, on delete cascade | Notebook owner |
| `title` | `varchar(255)` | Yes |  | Display title |
| `metadata` | `jsonb` | No | default `{}` | Extension data for notebook settings |
| `created_at` | `timestamptz` | No | default `now()` | Record creation time |
| `updated_at` | `timestamptz` | No | default `now()` | Record update time |

## Table: `pending_registrations`

Temporarily stores registration data while the user is waiting for OTP verification. A row in `users` is created only after OTP verification succeeds.

| Attribute | Type | Nullable | Constraint | Meaning |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Pending registration identifier |
| `email` | `varchar(255)` | No | Unique | Email waiting for verification |
| `password_hash` | `varchar(255)` | No |  | Hashed password; plain text passwords are not stored |
| `expires_at` | `timestamptz` | No |  | Registration verification expiration time |
| `created_at` | `timestamptz` | No | default `now()` | Record creation time |
| `updated_at` | `timestamptz` | No | default `now()` | Record update time |

## Table: `email_otps`

Stores email OTP records for `register` and `reset_password` flows.

| Attribute | Type | Nullable | Constraint | Meaning |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | OTP record identifier |
| `email` | `varchar(255)` | No | Index | Email that receives the OTP |
| `otp_hash` | `varchar(255)` | No |  | Hash of the OTP; the raw code is not stored |
| `purpose` | `varchar(32)` | No |  | Purpose: `register` or `reset_password` |
| `expires_at` | `timestamptz` | No |  | OTP expiration time |
| `is_used` | `boolean` | No | default `false` | Whether the OTP was already used |
| `created_at` | `timestamptz` | No | default `now()` | OTP creation time |

## Table: `refresh_tokens`

Stores refresh tokens for long-lived login sessions.

| Attribute | Type | Nullable | Constraint | Meaning |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Refresh token record identifier |
| `user_id` | `uuid` | No | FK -> `users.id`, index, on delete cascade | Token owner |
| `token_jti` | `varchar(255)` | No | Unique | Unique token identifier |
| `token_hash` | `varchar(255)` | No |  | Hash of the refresh token |
| `expires_at` | `timestamptz` | No |  | Token expiration time |
| `revoked_at` | `timestamptz` | Yes |  | Time the token was revoked |
| `last_used_at` | `timestamptz` | Yes |  | Most recent token use time |
| `user_agent` | `varchar(512)` | Yes |  | Browser or device user agent |
| `ip_address` | `varchar(64)` | Yes |  | Login or refresh IP address |
| `created_at` | `timestamptz` | No | default `now()` | Record creation time |

## Table: `documents`

Stores one record per uploaded file.

| Attribute | Type | Nullable | Constraint | Meaning |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Document identifier |
| `notebook_id` | `uuid` | Yes | FK -> `notebooks.id`, index, on delete set null | Owning notebook; `null` means public or legacy data |
| `storage_key` | `varchar(512)` | No | Unique | Storage path or object key |
| `original_file_name` | `varchar(255)` | No |  | Original uploaded file name |
| `mime_type` | `varchar(100)` | No | default `application/pdf` | File MIME type |
| `file_size_bytes` | `bigint` | Yes |  | File size |
| `total_pages` | `integer` | Yes |  | Number of document pages |
| `total_chunks` | `integer` | No | default `0` | Number of generated chunks |
| `status` | `document_status` | No | default `pending` | Processing status |
| `metadata` | `jsonb` | No | default `{}` | Extraction, storage, and indexing metadata |
| `created_at` | `timestamptz` | No | default `now()` | Record creation time |
| `updated_at` | `timestamptz` | No | default `now()` | Record update time |

## Table: `document_contents`

Stores extracted raw text for a document. This layer sits between the source file and generated chunks.

| Attribute | Type | Nullable | Constraint | Meaning |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Extracted content identifier |
| `document_id` | `uuid` | No | FK -> `documents.id`, unique, on delete cascade | The related document |
| `raw_text` | `text` | No |  | Full extracted text |
| `character_count` | `integer` | Yes |  | Number of characters in `raw_text` |
| `content_hash` | `varchar(64)` | Yes |  | Text hash for change detection |
| `extractor_name` | `varchar(255)` | Yes |  | Extraction tool or model name, such as `pypdf` |
| `metadata` | `jsonb` | No | default `{}` | Extraction metadata, warnings, layout data, or language data |
| `created_at` | `timestamptz` | No | default `now()` | Record creation time |
| `updated_at` | `timestamptz` | No | default `now()` | Record update time |

## Table: `document_chunks`

Stores small text chunks generated from `document_contents` for embedding and retrieval.

| Attribute | Type | Nullable | Constraint | Meaning |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Chunk identifier |
| `document_id` | `uuid` | No | FK -> `documents.id`, index, on delete cascade | Parent document |
| `chunk_index` | `integer` | No | Unique by `document_id + chunk_index`, check `>= 0` | Chunk order within the document |
| `page_from` | `integer` | Yes |  | First page covered by the chunk |
| `page_to` | `integer` | Yes |  | Last page covered by the chunk |
| `content` | `text` | No |  | Chunk text used for embedding and search |
| `token_count` | `integer` | Yes |  | Token count |
| `character_count` | `integer` | Yes |  | Character count |
| `qdrant_point_id` | `varchar(128)` | Yes | Unique | Related Qdrant point ID |
| `embedding_model` | `varchar(255)` | Yes |  | Embedding model used for the chunk |
| `metadata` | `jsonb` | No | default `{}` | Chunk overlap, section title, heading, or supplemental score data |
| `created_at` | `timestamptz` | No | default `now()` | Record creation time |

## Table: `chat_sessions`

Represents a conversation.

| Attribute | Type | Nullable | Constraint | Meaning |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Session identifier |
| `notebook_id` | `uuid` | Yes | FK -> `notebooks.id`, index, on delete set null | Owning notebook; `null` means public or anonymous session |
| `title` | `varchar(255)` | Yes |  | Display title |
| `metadata` | `jsonb` | No | default `{}` | Prompt preset, locale, retrieval filters, or UI state |
| `created_at` | `timestamptz` | No | default `now()` | Record creation time |
| `updated_at` | `timestamptz` | No | default `now()` | Record update time |

## Table: `chat_messages`

Stores individual messages in a chat session.

| Attribute | Type | Nullable | Constraint | Meaning |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Message identifier |
| `session_id` | `uuid` | No | FK -> `chat_sessions.id`, index, on delete cascade | Parent session |
| `reply_to_message_id` | `uuid` | Yes | Self FK -> `chat_messages.id`, index, on delete set null | Message being replied to |
| `role` | `message_role` | No |  | Message role: user, assistant, or system |
| `content` | `text` | No |  | Message text |
| `model_name` | `varchar(255)` | Yes |  | Model that generated the response |
| `prompt_tokens` | `integer` | Yes |  | Input token count |
| `completion_tokens` | `integer` | Yes |  | Output token count |
| `total_tokens` | `integer` | Yes |  | Total token count |
| `metadata` | `jsonb` | No | default `{}` | Latency, temperature, trace ID, or generation configuration |
| `created_at` | `timestamptz` | No | default `now()` | Record creation time |

## Table: `message_sources`

Stores chunks used to generate an assistant response. This supports retrieval traceability and source display.

| Attribute | Type | Nullable | Constraint | Meaning |
| --- | --- | --- | --- | --- |
| `id` | `uuid` | No | PK, default `gen_random_uuid()` | Source row identifier |
| `message_id` | `uuid` | No | FK -> `chat_messages.id`, index, on delete cascade | Assistant message that used this source |
| `chunk_id` | `uuid` | No | FK -> `document_chunks.id`, index, on delete restrict | Chunk used as a source |
| `source_rank` | `integer` | No | check `>= 1` | Source rank in the retrieval context |
| `score` | `float` | Yes |  | Similarity or rerank score |
| `snippet` | `text` | Yes |  | Short excerpt for UI or debugging |
| `created_at` | `timestamptz` | No | default `now()` | Time the source was attached to the message |

## Design Notes

- `metadata` uses `jsonb` in several tables so the model can evolve without immediate database versioning.
- `document_contents` exists so the system can re-chunk, re-embed, or debug extraction without reading the source PDF again.
- `qdrant_point_id` stores the mapping to the vector store; embeddings are not stored in PostgreSQL.
- `message_sources` is important for explainability because it records which chunks supported an answer.

## Recommended Insert Order

1. Create `users` when authentication is used.
2. Create `notebooks` for each user.
3. Create `documents`.
4. Extract text and create `document_contents`.
5. Chunk text and create `document_chunks`.
6. Create `chat_sessions`.
7. Create `chat_messages`.
8. Create `message_sources` for assistant messages.
