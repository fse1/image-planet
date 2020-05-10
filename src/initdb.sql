CREATE DATABASE IF NOT EXISTS imageplanet;
USE imageplanet;
CREATE TABLE IF NOT EXISTS users (userid BIGINT PRIMARY KEY AUTO_INCREMENT NOT NULL,
                                    username TEXT UNIQUE NOT NULL,
                                    profilepic TEXT,
                                    profiledesc TEXT,
                                    salt TEXT NOT NULL,
                                    passhash TEXT NOT NULL,
                                    sessioncookiehash TEXT UNIQUE,
                                    sessionexpiration DATE,
                                    csrftoken TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS images (imageid BIGINT PRIMARY KEY AUTO_INCREMENT NOT NULL,
                                     imgtitle TEXT NOT NULL,
                                     userid BIGINT NOT NULL,
                                     imgfile TEXT NOT NULL,
                                     imgdesc TEXT,
                                     likes BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS comments (imageid BIGINT NOT NULL,
                                       userid BIGINT NOT NULL,
                                       comtext TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS directmsg (dmid BIGINT PRIMARY KEY AUTO_INCREMENT NOT NULL,
                                        lowuserid BIGINT NOT NULL,
                                        highuserid BIGINT NOT NULL,
                                        lowuserread INT NOT NULL,
                                        highuserread INT NOT NULL);
CREATE TABLE IF NOT EXISTS messages (dmid BIGINT NOT NULL,
                                       userid BIGINT NOT NULL,
                                       msgtext TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS followers (userid BIGINT NOT NULL,
                                        followingthisuserid BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS likes (userid BIGINT NOT NULL,
                                    likesthisimageid BIGINT NOT NULL);