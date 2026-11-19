-- Signal Sleuth MySQL schema
CREATE DATABASE IF NOT EXISTS signalsleuth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE signalsleuth;

CREATE TABLE IF NOT EXISTS admins (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  email VARCHAR(255) NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pre_users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id VARCHAR(64) NOT NULL UNIQUE,
  full_name VARCHAR(255) NULL,
  sex VARCHAR(32) NULL,
  created_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id VARCHAR(64) NOT NULL UNIQUE,
  campus_id VARCHAR(64) NULL,
  full_name VARCHAR(255) NULL,
  generated_username VARCHAR(64) NOT NULL UNIQUE,
  sex VARCHAR(32) NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  status_chapter INT NOT NULL DEFAULT 1,
  overall_points DOUBLE NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  INDEX (generated_username),
  INDEX (email)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS password_reset_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  temp_password VARCHAR(128) NULL,
  created_at DATETIME NOT NULL,
  resolved_at DATETIME NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS season (
  id INT PRIMARY KEY,
  name VARCHAR(255) NULL,
  start_date DATE NULL,
  end_date DATE NULL,
  updated_at DATETIME NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS chapters (
  chapter_num INT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  is_active TINYINT NOT NULL DEFAULT 0,
  activated_at DATETIME NULL,
  start_date DATE NULL,
  end_date DATE NULL,
  game_filename VARCHAR(255) NULL,
  game_uploaded_at DATETIME NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS level_scores (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  chapter_num INT NOT NULL,
  level_num INT NOT NULL,
  best_score INT NOT NULL DEFAULT 0,
  max_score INT NOT NULL,
  attempts INT NOT NULL DEFAULT 0,
  cleared TINYINT NOT NULL DEFAULT 0,
  is_rereg TINYINT NOT NULL DEFAULT 0,
  feedback_json LONGTEXT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uq_user_ch_lv (user_id, chapter_num, level_num),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS chapter_progress (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  chapter_num INT NOT NULL,
  total_score INT NOT NULL DEFAULT 0,
  max_possible INT NOT NULL DEFAULT 0,
  levels_cleared INT NOT NULL DEFAULT 0,
  is_rereg TINYINT NOT NULL DEFAULT 0,
  passed TINYINT NOT NULL DEFAULT 0,
  effective_score DOUBLE NOT NULL DEFAULT 0,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uq_user_ch (user_id, chapter_num),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rereg_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  chapter_num INT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  created_at DATETIME NOT NULL,
  resolved_at DATETIME NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rank_snapshots (
  id INT AUTO_INCREMENT PRIMARY KEY,
  week_label VARCHAR(64) NOT NULL,
  week_start DATE NOT NULL,
  snapshot_type VARCHAR(32) NOT NULL DEFAULT 'weekly',
  created_at DATETIME NOT NULL,
  UNIQUE KEY uq_week_type (week_label, snapshot_type)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rank_snapshot_rows (
  id INT AUTO_INCREMENT PRIMARY KEY,
  snapshot_id INT NOT NULL,
  user_id INT NOT NULL,
  rank_pos INT NOT NULL,
  overall_score DOUBLE NOT NULL,
  chapters_passed INT NOT NULL DEFAULT 0,
  any_rereg TINYINT NOT NULL DEFAULT 0,
  FOREIGN KEY (snapshot_id) REFERENCES rank_snapshots(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS email_log (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  email_to VARCHAR(255) NOT NULL,
  subject VARCHAR(255) NOT NULL,
  body TEXT NULL,
  status VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS question_bank (
  id INT AUTO_INCREMENT PRIMARY KEY,
  chapter_num INT NOT NULL,
  level_num INT NOT NULL,
  q_index INT NOT NULL,
  level_title VARCHAR(255) NULL,
  question_text TEXT NOT NULL,
  points INT NOT NULL DEFAULT 0,
  model_answer TEXT NULL,
  keys_json LONGTEXT NULL,
  feedback_note TEXT NULL,
  updated_at DATETIME NULL,
  UNIQUE KEY uq_ch_lv_q (chapter_num, level_num, q_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Architecture expansion (proposed modules) ───────────────

CREATE TABLE IF NOT EXISTS courses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(64) NOT NULL UNIQUE,
  title VARCHAR(255) NOT NULL,
  description TEXT NULL,
  is_active TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS game_versions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  chapter_num INT NOT NULL,
  version_label VARCHAR(64) NOT NULL,
  filename VARCHAR(255) NOT NULL,
  storage_key VARCHAR(512) NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'published',
  notes TEXT NULL,
  uploaded_by_admin_id INT NULL,
  created_at DATETIME NOT NULL,
  INDEX (chapter_num),
  INDEX (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS levels (
  id INT AUTO_INCREMENT PRIMARY KEY,
  chapter_num INT NOT NULL,
  level_num INT NOT NULL,
  title VARCHAR(255) NOT NULL,
  sequence_order INT NOT NULL DEFAULT 1,
  pass_percent DOUBLE NOT NULL DEFAULT 50.0,
  is_active TINYINT NOT NULL DEFAULT 1,
  UNIQUE KEY uq_ch_level (chapter_num, level_num)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS game_questions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  chapter_num INT NOT NULL,
  level_num INT NOT NULL,
  q_index INT NOT NULL,
  question_text TEXT NOT NULL,
  points INT NOT NULL DEFAULT 0,
  model_answer TEXT NULL,
  keys_json LONGTEXT NULL,
  feedback_note TEXT NULL,
  is_active TINYINT NOT NULL DEFAULT 1,
  UNIQUE KEY uq_gq (chapter_num, level_num, q_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS game_attempts (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  chapter_num INT NOT NULL,
  level_num INT NOT NULL,
  attempt_no INT NOT NULL DEFAULT 1,
  score INT NOT NULL DEFAULT 0,
  max_score INT NOT NULL DEFAULT 0,
  cleared TINYINT NOT NULL DEFAULT 0,
  answers_json LONGTEXT NULL,
  feedback_json LONGTEXT NULL,
  created_at DATETIME NOT NULL,
  INDEX (user_id, chapter_num, level_num),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS student_achievements (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  code VARCHAR(64) NOT NULL,
  title VARCHAR(255) NOT NULL,
  meta_json TEXT NULL,
  awarded_at DATETIME NOT NULL,
  UNIQUE KEY uq_user_code (user_id, code),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  audience VARCHAR(32) NOT NULL DEFAULT 'user',
  title VARCHAR(255) NOT NULL,
  body TEXT NULL,
  is_read TINYINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  INDEX (user_id),
  INDEX (audience)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS admin_activity_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  admin_id INT NULL,
  action VARCHAR(128) NOT NULL,
  detail TEXT NULL,
  ip VARCHAR(64) NULL,
  created_at DATETIME NOT NULL,
  INDEX (admin_id),
  INDEX (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  actor_type VARCHAR(32) NOT NULL,
  actor_id INT NULL,
  event_type VARCHAR(128) NOT NULL,
  entity_type VARCHAR(64) NULL,
  entity_id VARCHAR(64) NULL,
  detail TEXT NULL,
  created_at DATETIME NOT NULL,
  INDEX (event_type),
  INDEX (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS system_settings (
  setting_key VARCHAR(128) PRIMARY KEY,
  setting_value TEXT NULL,
  updated_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS users_extra (
  user_id INT PRIMARY KEY,
  is_suspended TINYINT NOT NULL DEFAULT 0,
  course_id INT NULL,
  cohort VARCHAR(64) NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
