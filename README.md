# Image Planet
## Description
Image Planet is a social media site focused on image sharing.

Users will be able to:
* Create an Account
* Upload Images
* Like and Comment on Uploaded Images
* Follow Other Users And See Their Follower's Images on the Home Page
* Direct Message Other Users

## Deployment
Image Planet can be easily deployed with Docker Compose.

1. Clone the repository.
2. Enter the cloned repository and open the `docker-compose.yml` file.
  * At a minimum, change the values of `MYSQL_PASSWORD` and `MYSQL_ROOT_PASSWORD` to be strong, unique passwords. Don't forget to update the value of `DB_PASS` to be equivalent to the value you selected for `MYSQL_PASSWORD`.
  * In additon, you may want to alter the values of `MYSQL_USER` (and `DB_USER`).
  * Optionally, you may want to change the local port of the app.
3. Run `docker-compose build` in the root directory of the repository. Then, run `docker-compose up`.
4. Access the application by navigating a web browser to `127.0.0.1:8080` (if you changed the local port in step 2, use that port number instead of 8080).
