%% ERD v1 — Greenfield Personel Operasyon Platformu

erDiagram
    USERS {
        uuid user_id PK
        string email UK
        string password_hash
        string status
        datetime created_at
    }

    ROLES {
        uuid role_id PK
        string role_key UK
        string role_name
    }

    PERMISSIONS {
        uuid permission_id PK
        string permission_key UK
        string description
    }

    USER_ROLES {
        uuid user_id FK
        uuid role_id FK
    }

    ROLE_PERMISSIONS {
        uuid role_id FK
        uuid permission_id FK
    }

    AUDIT_LOGS {
        uuid audit_id PK
        uuid actor_user_id FK
        string action
        string entity_type
        string entity_id
        json old_value
        json new_value
        datetime created_at
    }

    EMPLOYEES {
        uuid employee_id PK
        string national_id UK
        string first_name
        string last_name
        string department_code
        string title_code
        string status
        date start_date
        date leave_date
        datetime created_at
        datetime updated_at
    }

    EMPLOYEE_STATUS_HISTORY {
        uuid history_id PK
        uuid employee_id FK
        string old_status
        string new_status
        datetime changed_at
        uuid changed_by FK
    }

    LEAVE_POLICIES {
        uuid policy_id PK
        string leave_type UK
        integer max_days
        boolean triggers_passive
        boolean active
    }

    LEAVE_REQUESTS {
        uuid leave_request_id PK
        uuid employee_id FK
        string leave_type
        date start_date
        date end_date
        numeric days
        string status
        string reason
        datetime created_at
    }

    LEAVE_BALANCES {
        uuid balance_id PK
        uuid employee_id FK
        numeric annual_entitled
        numeric annual_used
        numeric annual_remaining
        numeric sua_entitled
        numeric sua_used
        numeric sua_remaining
        datetime updated_at
    }

    DOCUMENTS {
        uuid document_id PK
        string file_name
        string mime_type
        bigint file_size
        string checksum
        string storage_key
        datetime uploaded_at
        uuid uploaded_by FK
    }

    DOCUMENT_LINKS {
        uuid link_id PK
        uuid document_id FK
        string entity_type
        string entity_id
    }

    USERS ||--o{ USER_ROLES : has
    ROLES ||--o{ USER_ROLES : maps
    ROLES ||--o{ ROLE_PERMISSIONS : grants
    PERMISSIONS ||--o{ ROLE_PERMISSIONS : includes

    USERS ||--o{ AUDIT_LOGS : acts

    EMPLOYEES ||--o{ EMPLOYEE_STATUS_HISTORY : tracks
    USERS ||--o{ EMPLOYEE_STATUS_HISTORY : changes

    EMPLOYEES ||--o{ LEAVE_REQUESTS : requests
    EMPLOYEES ||--|| LEAVE_BALANCES : owns
    LEAVE_POLICIES ||--o{ LEAVE_REQUESTS : governs

    DOCUMENTS ||--o{ DOCUMENT_LINKS : links
    USERS ||--o{ DOCUMENTS : uploads
