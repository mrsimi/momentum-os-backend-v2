-- USERS
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_guest BOOLEAN DEFAULT FALSE,
    date_created TIMESTAMPTZ DEFAULT now(),
    date_updated TIMESTAMPTZ DEFAULT now(),
    last_login TIMESTAMPTZ DEFAULT now(),
    is_verified BOOLEAN DEFAULT FALSE,
    to_changepassword BOOLEAN
);

-- PROJECTS
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    title VARCHAR UNIQUE NOT NULL,
    description VARCHAR,
    creator_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    date_created TIMESTAMPTZ DEFAULT now(),
    date_updated TIMESTAMPTZ DEFAULT now(),
    is_active BOOLEAN DEFAULT TRUE,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    has_ended BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_project_creator_user_id ON projects (creator_user_id);

-- CHECKINS
CREATE TABLE checkins (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    user_checkin_time TIME NOT NULL,
    user_checkin_days TEXT[] NOT NULL,
    user_timezone VARCHAR NOT NULL,
    checkin_time_utc TIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    date_created TIMESTAMPTZ DEFAULT now(),
    date_updated TIMESTAMPTZ DEFAULT now(),
    last_run_time_utc TIME,
    project_ended BOOLEAN DEFAULT FALSE,
    checkin_days_utc TEXT[] NOT NULL
);

CREATE INDEX idx_checkin_project_id ON checkins (project_id);

-- PROJECT MEMBERS
CREATE TABLE project_members (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    date_created TIMESTAMPTZ DEFAULT now(),
    date_updated TIMESTAMPTZ DEFAULT now(),
    is_active BOOLEAN DEFAULT FALSE,
    is_creator BOOLEAN DEFAULT FALSE,
    is_guest BOOLEAN DEFAULT FALSE,
    is_member BOOLEAN DEFAULT FALSE,
    user_email VARCHAR,
    has_accepted BOOLEAN DEFAULT FALSE,
    has_rejected BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_project_member_project_id ON project_members (project_id);
CREATE INDEX idx_project_member_user_id ON project_members (user_id);

-- CHECKIN RESPONSES
CREATE TABLE checkin_responses (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    team_member_id INTEGER REFERENCES project_members(id) ON DELETE SET NULL,
    date_usertz TIMESTAMPTZ NOT NULL,
    date_utctz TIMESTAMPTZ NOT NULL,
    did_yesterday TEXT,
    doing_today TEXT,
    blocker TEXT,
    checkin_day VARCHAR,
    checkin_id INTEGER REFERENCES checkins(id) ON DELETE CASCADE,
    date_created_utc TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_checkin_response_project_id ON checkin_responses (project_id);
CREATE INDEX idx_checkin_response_member_id ON checkin_responses (team_member_id);
CREATE INDEX idx_checkin_response_checkin_id ON checkin_responses (checkin_id);
