CREATE TABLE IF NOT EXISTS users (
    id           uuid        PRIMARY KEY,
    student_id   text        UNIQUE,
    name         text        NOT NULL,
    last_name    text        NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    owner        uuid        NOT NULL REFERENCES users(id),
    name         text        NOT NULL,
    
    UNIQUE (owner, name)
);

CREATE TABLE IF NOT EXISTS jobs (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    owner        uuid        NOT NULL REFERENCES users(id),
    kind         text        NOT NULL CHECK (kind IN ('run', 'submission')),
    project      uuid        REFERENCES projects(id) ON DELETE CASCADE, -- null for submissions
    status       text        NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'done', 'failed')),
    request_key  text        NOT NULL,
    result_key   text,
    result_saved boolean     NOT NULL DEFAULT false,
    created_at   timestamptz NOT NULL DEFAULT now(),
    started_at   timestamptz,
    
    CHECK ((kind = 'run') = (project IS NOT NULL))
);