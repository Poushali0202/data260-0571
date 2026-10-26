USE s0571_rel;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS users;
CREATE TABLE users (
  id int NOT NULL AUTO_INCREMENT,
  username varchar(50) NOT NULL,
  password_hash varchar(255) NOT NULL,
  role varchar(20) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY username (username),
  CONSTRAINT ck_user_role CHECK (role IN ('reader', 'writer', 'moderator'))
);
