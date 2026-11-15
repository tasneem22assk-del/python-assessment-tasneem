import sqlite3
con= sqlite3.connect('tickets.db')
cursor = con.cursor()
PRAGMA   FOREIGN_KEY = ON

CREATE TABLE  users (
    id INT NOT NULL auto_increment,
   username  NOT NULL UNIQUE,
    primary key (id)
    );


CREATE TABLE tickets (
    id INTEGER PRIMARY KEY,
    title  TEXT NOT NULL,
    assignee_id INTEGER NULL REFERENCES users(id),
    status1   TEXT NOT NULL DEFAULT 'OPEN'
                CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')),
    priority    TEXT NOT NULL
                CHECK (priority IN ('HIGH', 'MEDIUM', 'LOW'))
);
insert into users ( username) VALUE ('Ali');
insert into users (username) VALUE ('Maya');


insert into tickets(id, title,assignee_id,status,priority ) value (1,"VPN access",9,"OPEN",'HIGH');
insert into tickets(id, title,assignee_id,status,priority ) value (2,"VPN access",2,"IN_PROGRESS","MEDIUM");
insert into tickets(id, title,assignee_id,status,priority ) value (2,"VPN access",6,"RESOLVED","LOW");




