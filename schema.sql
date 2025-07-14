-- AI Tutor Database Schema
-- This file contains the SQL schema for the AI Tutor application

-- Create student sessions table
CREATE TABLE IF NOT EXISTS student_sessions (
    student_id VARCHAR(20) PRIMARY KEY,
    current_step_index INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    session_start_time TIMESTAMP DEFAULT NOW(),
    total_interactions INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    last_message_content TEXT
);

-- Create pitch evaluations table
CREATE TABLE IF NOT EXISTS pitch_evaluations (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(20),
    pitch_content TEXT,
    evaluation_score INTEGER,
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (student_id) REFERENCES student_sessions(student_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_student_sessions_updated ON student_sessions(last_updated);
CREATE INDEX IF NOT EXISTS idx_pitch_evaluations_student ON pitch_evaluations(student_id);
CREATE INDEX IF NOT EXISTS idx_pitch_evaluations_created ON pitch_evaluations(created_at);

-- Insert sample data (optional, for testing)
-- INSERT INTO student_sessions (student_id, current_step_index, total_interactions) 
-- VALUES ('12345678', 0, 0) ON CONFLICT (student_id) DO NOTHING;
