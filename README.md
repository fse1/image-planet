# CSE 312 Group Project (Spring 2020)
## Basic Site Idea
Our site is designed to allow users to share images in a social fashion.

Users will be able to:
* Create an Account
* Upload Images
* Like and Comment on Uploaded Images
* Follow Other Users And See Their Follower's Images on the Home Page
* Direct Message Other Users

## Database Info
Use the following commands for the database.
* CREATE DATABASE IF NOT EXISTS imageplanet;
* USE imageplanet;
* CREATE TABLE IF NOT EXISTS users (userid BIGINT PRIMARY KEY AUTO_INCREMENT NOT NULL, 
                                    username TEXT UNIQUE NOT NULL, 
                                    profilepic BIGINT,
                                    profiledesc TEXT,
                                    salt TEXT NOT NULL,
                                    passhash TEXT NOT NULL,
                                    sessioncookie TEXT UNIQUE,
                                    sessionexpiration DATE,
                                    csrftoken TEXT UNIQUE);
* CREATE TABLE IF NOT EXISTS images (imageid BIGINT PRIMARY KEY AUTO_INCREMENT NOT NULL, 
                                     imgtitle TEXT NOT NULL, 
                                     userid BIGINT NOT NULL,
                                     imgfile TEXT NOT NULL,
                                     imgdesc TEXT,
                                     likes BIGINT NOT NULL);
* CREATE TABLE IF NOT EXISTS comments (comid BIGINT PRIMARY KEY AUTO_INCREMENT NOT NULL, 
                                       imageid BIGINT NOT NULL,
                                       userid BIGINT NOT NULL, 
                                       comtext TEXT NOT NULL);    
* CREATE TABLE IF NOT EXISTS directmsg (dmid BIGINT PRIMARY KEY AUTO_INCREMENT NOT NULL,
                                        lowuserid BIGINT NOT NULL, 
                                        highuserid BIGINT NOT NULL); 
* CREATE TABLE IF NOT EXISTS messages (msgid BIGINT PRIMARY KEY AUTO_INCREMENT NOT NULL, 
                                       dmid BIGINT NOT NULL,
                                       userid BIGINT NOT NULL, 
                                       msgtext TEXT NOT NULL);                                         
* CREATE TABLE IF NOT EXISTS followers (followid BIGINT PRIMARY KEY AUTO_INCREMENT NOT NULL, 
                                        userid BIGINT NOT NULL, 
                                        followingthisuserid BIGINT NOT NULL); 
* CREATE TABLE IF NOT EXISTS likes (likeid BIGINT PRIMARY KEY AUTO_INCREMENT NOT NULL, 
                                    userid BIGINT NOT NULL, 
                                    likesthisimageid BIGINT NOT NULL);                                          
                                        
                                    
                                    
                                    
                                    
                                    


