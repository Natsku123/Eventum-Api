CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT,
  password VARCHAR(255) NOT NULL,
  username VARCHAR(255) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE (password, username)
) ENGINE=INNODB CHARSET=utf8;
#
CREATE TABLE IF NOT EXISTS events (
  id INT AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  description VARCHAR(255),
  template VARCHAR(255) NOT NULL,
  updated DATE,
  expire DATE,
  available SMALLINT(4),
  PRIMARY KEY (id),
  UNIQUE (template)
) ENGINE=INNODB CHARSET=utf8;
#
CREATE TABLE IF NOT EXISTS eventImages (
  id INT AUTO_INCREMENT,
  event_id INT NOT NULL,
  image VARCHAR(255),
  PRIMARY KEY (id),
  UNIQUE (image),
  FOREIGN KEY (event_id) REFERENCES events(id)
) ENGINE=INNODB CHARSET=utf8;
#
CREATE TABLE IF NOT EXISTS roles (
  id INT AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  power SMALLINT(4),
  PRIMARY KEY (id)
) ENGINE=INNODB CHARSET=utf8;
#
INSERT INTO roles (name, power) VALUES ('Member', 3);
#
INSERT INTO roles (name, power) VALUES ('Other', 1);
#
CREATE TABLE IF NOT EXISTS humans (
  id INT AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  signed DATE NOT NULL,
  role_id INT,
  PRIMARY KEY (id),
  UNIQUE (email),
  FOREIGN KEY (role_id) REFERENCES roles(id)
) ENGINE=INNODB CHARSET=utf8;
#
CREATE TABLE IF NOT EXISTS eventParticipants (
  id INT AUTO_INCREMENT,
  event_id INT NOT NULL,
  human_id INT NOT NULL,
  form VARCHAR(255),
  paid SMALLINT(2),
  PRIMARY KEY (id),
  UNIQUE (form),
  FOREIGN KEY (event_id) REFERENCES events (id),
  FOREIGN KEY (human_id) REFERENCES humans (id)
) ENGINE=INNODB CHARSET=utf8;
#
CREATE TABLE IF NOT EXISTS prices (
  id INT AUTO_INCREMENT,
  event_id INT NOT NULL,
  role_id INT NOT NULL,
  price INT NOT NULL,
  PRIMARY KEY (id),
  FOREIGN KEY (event_id) REFERENCES events (id),
  FOREIGN KEY (role_id) REFERENCES roles (id)
) ENGINE=INNODB CHARSET=utf8;
#
CREATE TABLE IF NOT EXISTS limits (
  id INT AUTO_INCREMENT,
  event_id INT NOT NULL,
  role_id INT,
  size INT,
  filled INT,
  PRIMARY KEY (id),
  FOREIGN KEY (event_id) REFERENCES events (id),
  FOREIGN KEY (role_id) REFERENCES roles (id)
) ENGINE=INNODB CHARSET=utf8;