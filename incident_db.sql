CREATE DATABASE incident_db;
USE incident_db;

CREATE TABLE tbl_rol (
  id_rol INT PRIMARY KEY AUTO_INCREMENT,
  name_rol VARCHAR(100) NOT NULL
);

CREATE TABLE tbl_user (
  id_user INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(100) NOT NULL,
  password VARCHAR(255) NOT NULL,
  id_rol INT,
  FOREIGN KEY (id_rol) REFERENCES tbl_rol(id_rol)
);

CREATE TABLE tbl_status (
  id_status INT PRIMARY KEY AUTO_INCREMENT,
  name_status VARCHAR(100) NOT NULL
);

CREATE TABLE tbl_incident (
  id_incident INT PRIMARY KEY AUTO_INCREMENT,
  incident_type VARCHAR(100) NOT NULL,
  incident_info TEXT NOT NULL,
  incident_date DATE NOT NULL,
  incident_image VARCHAR(255),
  incident_coment TEXT NULL,
  create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  id_user INT,
  id_status INT,
  FOREIGN KEY (id_user) REFERENCES tbl_user(id_user),
  FOREIGN KEY (id_status) REFERENCES tbl_status(id_status)
);

CREATE TABLE tbl_notification (
  id_notification INT PRIMARY KEY AUTO_INCREMENT,
  body VARCHAR(255) NOT NULL,
  user_id INT,
  FOREIGN KEY (user_id) REFERENCES tbl_user(id_user)
);