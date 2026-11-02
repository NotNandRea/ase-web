CREATE TABLE IF NOT EXISTS jobs (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    status       text        NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending', 'running', 'done', 'failed')),
    request_key  text        NOT NULL,
    result_key   text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    started_at   timestamptz
);